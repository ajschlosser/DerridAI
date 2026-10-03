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
import WorkMetadataLlmDialog from "../../src/components/WorkMetadataLlmDialog.vue";
import {
  closeWorkMetadataLlmDialog,
  openWorkMetadataLlmDialog,
  useWorkMetadataLlmDialog,
} from "../../src/composables/workMetadataLlmDialog";

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
  closeWorkMetadataLlmDialog();
});

const profiles = [
  { id: "a", name: "A", type: "ollama", model: "m1" },
  { id: "b", name: "B", type: "openai", model: "m2" },
] as never;

function open(overrides = {}) {
  const start = vi.fn().mockResolvedValue(undefined);
  const manageProviders = vi.fn().mockResolvedValue(true);
  openWorkMetadataLlmDialog({
    scopeCount: 8,
    scopeSummary: "8 Book",
    sample: [{ work: "W", sourceTypeLabel: "Book" }],
    profiles,
    defaultProfileId: "b",
    start,
    manageProviders,
    ...overrides,
  });
  return { start, manageProviders };
}

describe("WorkMetadataLlmDialog", () => {
  it("starts with the default profile and closes on success", async () => {
    const wrapper = mount(WorkMetadataLlmDialog, { attachTo: document.body });
    const { start } = open();
    await flushPromises();
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(start).toHaveBeenCalledWith("b");
    expect(useWorkMetadataLlmDialog().current.value).toBeNull();
    wrapper.unmount();
  });

  it("stays open when the lookup fails so the user can retry", async () => {
    const wrapper = mount(WorkMetadataLlmDialog, { attachTo: document.body });
    open({ start: vi.fn().mockRejectedValue(new Error("boom")) });
    await flushPromises();
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(useWorkMetadataLlmDialog().current.value).not.toBeNull();
    expect(wrapper.find("button.btn.primary").attributes("disabled")).toBeUndefined();
    wrapper.unmount();
  });

  it("disables starting when there is no provider profile", async () => {
    const wrapper = mount(WorkMetadataLlmDialog, { attachTo: document.body });
    open({ profiles: [], defaultProfileId: "" });
    await flushPromises();
    expect(wrapper.find("button.btn.primary").attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("shows how many groups the sample leaves out", async () => {
    const wrapper = mount(WorkMetadataLlmDialog, { attachTo: document.body });
    open();
    await flushPromises();
    expect(wrapper.find(".work-metadata-sample").text()).toContain("+7");
    wrapper.unmount();
  });
});
