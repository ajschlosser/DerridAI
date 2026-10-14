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

import PdfDraftRecordDialog from "../../src/components/PdfDraftRecordDialog.vue";
import {
  closePdfDraftRecordDialog,
  openPdfDraftRecordDialog,
  type PdfDraftRecordRequest,
} from "../../src/composables/pdfDraftRecordDialog";

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
  closePdfDraftRecordDialog();
});

function open(save: PdfDraftRecordRequest["save"], over: Partial<PdfDraftRecordRequest> = {}) {
  openPdfDraftRecordDialog({
    title: "Work",
    page: 3,
    recordJson: '{"text":"x"}',
    files: [{ id: "f1", name: "a.jsonl", count: 2 }],
    stores: [{ id: "s1", name: "s1", count: 5 }],
    save,
    ...over,
  });
}

describe("PdfDraftRecordDialog", () => {
  it("submits the edited JSON with the chosen destinations and closes on success", async () => {
    const wrapper = mount(PdfDraftRecordDialog, { attachTo: document.body });
    const save = vi.fn(async () => true);
    open(save);
    await flushPromises();
    await wrapper.find("textarea").setValue('{"text":"edited"}');
    await wrapper.find("#pdfDraftFile").setValue("f1");
    await wrapper.find("#pdfDraftStore").setValue("s1");
    await wrapper.find(".btn.primary").trigger("click");
    await flushPromises();
    expect(save).toHaveBeenCalledWith({
      json: '{"text":"edited"}',
      fileId: "f1",
      storeName: "s1",
    });
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });

  it("stays open, keeping the edits, when the save is rejected", async () => {
    const wrapper = mount(PdfDraftRecordDialog, { attachTo: document.body });
    open(async () => false);
    await flushPromises();
    await wrapper.find("textarea").setValue("not json");
    await wrapper.find(".btn.primary").trigger("click");
    await flushPromises();
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    expect((wrapper.find("textarea").element as HTMLTextAreaElement).value).toBe("not json");
    wrapper.unmount();
  });

  it("disables the Chroma destination when there are no stores", async () => {
    const wrapper = mount(PdfDraftRecordDialog, { attachTo: document.body });
    open(async () => true, { stores: [] });
    await flushPromises();
    expect(wrapper.find("#pdfDraftStore").attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });
});
