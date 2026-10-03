/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import RecordHistoryDialog from "../../src/components/RecordHistoryDialog.vue";
import {
  closeRecordHistoryDialog,
  openRecordHistoryDialog,
  useRecordHistoryDialog,
  type RecordHistoryVersion,
} from "../../src/composables/recordHistoryDialog";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

beforeEach(() => {
  setActivePinia(createPinia());
  closeRecordHistoryDialog();
});

function open(over: Record<string, unknown> = {}) {
  let versions: RecordHistoryVersion[] = [
    { label: "Original", record: { work: "A", year: "1967", text: "one two" } },
    { label: "Change 1", source: "manual", record: { work: "A", year: "1976", text: "one two" } },
  ];
  const request = {
    recordId: "rec-1",
    versions: () => versions,
    changedFields: (a: Record<string, unknown>, b: Record<string, unknown>) =>
      Object.keys(b).filter((k) => a[k] !== b[k]),
    fieldLabel: (field: string) => field,
    formatValue: (value: unknown) => String(value),
    formatTimestamp: (value: string) => value,
    restore: vi.fn().mockResolvedValue(true),
    restoreOriginal: vi.fn().mockResolvedValue(true),
    clear: vi.fn().mockResolvedValue(true),
    ...over,
  };
  openRecordHistoryDialog(request);
  return { request, setVersions: (next: RecordHistoryVersion[]) => (versions = next) };
}

const button = (wrapper: ReturnType<typeof mount>, label: string) =>
  wrapper.findAll("button").find((b) => b.text().includes(label))!;

describe("RecordHistoryDialog", () => {
  it("opens on the newest version and walks back to the original", async () => {
    const wrapper = mount(RecordHistoryDialog, { attachTo: document.body });
    open();
    await flushPromises();
    expect(wrapper.find(".history-version-position").text()).toContain("Change 1");
    expect(wrapper.find(".history-version-diff").text()).toContain("year");
    await button(wrapper, "Older").trigger("click");
    expect(wrapper.find(".history-version-position").text()).toContain("Original");
    expect(wrapper.find(".history-version-diff").exists()).toBe(false);
    expect(button(wrapper, "Older").attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("cannot restore the current version", async () => {
    const wrapper = mount(RecordHistoryDialog, { attachTo: document.body });
    const { request } = open();
    await flushPromises();
    const restore = button(wrapper, "Restore this version");
    expect(restore.attributes("disabled")).toBeDefined();
    await restore.trigger("click");
    expect(request.restore).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("restores the selected version and re-reads the list", async () => {
    const wrapper = mount(RecordHistoryDialog, { attachTo: document.body });
    const { request, setVersions } = open();
    await flushPromises();
    await button(wrapper, "Older").trigger("click");
    request.restore.mockImplementation(async () => {
      setVersions([
        { label: "Original", record: { work: "A", year: "1967", text: "one two" } },
        { label: "Change 1", record: { work: "A", year: "1976", text: "one two" } },
        { label: "Change 2", record: { work: "A", year: "1967", text: "one two" } },
      ]);
      return true;
    });
    await button(wrapper, "Restore this version").trigger("click");
    await flushPromises();
    expect(request.restore).toHaveBeenCalledWith(expect.objectContaining({ label: "Original" }));
    expect(wrapper.find(".history-version-position").text()).toContain("Change 2");
    wrapper.unmount();
  });

  it("closes after the audit trail is deleted, and stays open when declined", async () => {
    const wrapper = mount(RecordHistoryDialog, { attachTo: document.body });
    const { request } = open({
      clear: vi.fn().mockResolvedValueOnce(false).mockResolvedValue(true),
    });
    await flushPromises();
    await button(wrapper, "Delete audit history").trigger("click");
    await flushPromises();
    expect(useRecordHistoryDialog().current.value).not.toBeNull();
    await button(wrapper, "Delete audit history").trigger("click");
    await flushPromises();
    expect(request.clear).toHaveBeenCalledTimes(2);
    expect(useRecordHistoryDialog().current.value).toBeNull();
    wrapper.unmount();
  });
});
