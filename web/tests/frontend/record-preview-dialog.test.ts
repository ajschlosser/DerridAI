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

import RecordPreviewDialog from "../../src/components/RecordPreviewDialog.vue";
import {
  closeRecordPreviewDialog,
  openRecordPreviewDialog,
  type RecordPreviewRequest,
} from "../../src/composables/recordPreviewDialog";

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
  closeRecordPreviewDialog();
});

function open(over: Partial<RecordPreviewRequest> = {}) {
  const request: RecordPreviewRequest = {
    recordId: "rec-1",
    subtitle: "Work · file.jsonl",
    stale: false,
    summary: { work: "Work", pages: "3", citation: "—", proposalCount: 1, needsReview: false },
    fields: [{ key: "speaker", label: "Speaker", value: '"A"', proposed: true }],
    text: "some text",
    proposals: [{ label: "Speaker", current: '"A"', proposed: '"B"', rationale: "because" }],
    history: [],
    copyKey: "f::0",
    openFull: vi.fn(),
    ...over,
  };
  openRecordPreviewDialog(request);
  return request;
}

describe("RecordPreviewDialog", () => {
  it("shows the current and proposed values side by side, and warns when stale", async () => {
    const wrapper = mount(RecordPreviewDialog, { attachTo: document.body });
    open({ stale: true });
    await flushPromises();
    expect(wrapper.find(".info.warn").exists()).toBe(true);
    expect(wrapper.find(".proposed-field").exists()).toBe(true);
    const grid = wrapper.find(".record-preview-proposal-grid");
    expect(grid.text()).toContain('"A"');
    expect(grid.text()).toContain('"B"');
    expect(wrapper.find(".record-preview-proposals small").text()).toBe("because");
    wrapper.unmount();
  });

  it("omits the stale notice and proposals when there are none, and notes the empty audit trail", async () => {
    const wrapper = mount(RecordPreviewDialog, { attachTo: document.body });
    open({ proposals: [] });
    await flushPromises();
    expect(wrapper.find(".info.warn").exists()).toBe(false);
    expect(wrapper.find(".record-preview-proposals").exists()).toBe(false);
    expect(wrapper.find(".record-preview-history .note").exists()).toBe(true);
    wrapper.unmount();
  });

  it("closes before opening the full record, and keeps the copy key for the page handler", async () => {
    const wrapper = mount(RecordPreviewDialog, { attachTo: document.body });
    const request = open();
    await flushPromises();
    expect(wrapper.find("[data-copy-row-key]").attributes("data-copy-row-key")).toBe("f::0");
    await wrapper.find(".btn.primary").trigger("click");
    await flushPromises();
    expect(request.openFull).toHaveBeenCalled();
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });
});
