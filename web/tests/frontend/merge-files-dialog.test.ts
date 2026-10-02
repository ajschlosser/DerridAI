// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import MergeFilesDialog from "../../src/components/MergeFilesDialog.vue";
import {
  closeMergeFilesDialog,
  openMergeFilesDialog,
  useMergeFilesDialog,
} from "../../src/composables/mergeFilesDialog";

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
  closeMergeFilesDialog();
});

function open(merge = vi.fn().mockResolvedValue(true)) {
  openMergeFilesDialog({
    files: [
      { id: "a", name: "a.jsonl", recordCount: 2 },
      { id: "b", name: "b.jsonl", recordCount: 3 },
    ],
    defaultName: "merged.jsonl",
    merge,
  });
  return merge;
}

describe("MergeFilesDialog", () => {
  it("merges every tab by default with the default name, then closes", async () => {
    const wrapper = mount(MergeFilesDialog, { attachTo: document.body });
    const merge = open();
    await flushPromises();
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(merge).toHaveBeenCalledWith({
      fileIds: ["a", "b"],
      name: "merged.jsonl",
      download: false,
    });
    expect(useMergeFilesDialog().current.value).toBeNull();
    wrapper.unmount();
  });

  it("sends only the ticked tabs, the edited name and the download choice", async () => {
    const wrapper = mount(MergeFilesDialog, { attachTo: document.body });
    const merge = open();
    await flushPromises();
    await wrapper.findAll(".merge-file-item input")[0].setValue(false);
    await wrapper.find("#mergeFilesName").setValue("x");
    await wrapper.find(".check-item input").setValue(true);
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(merge).toHaveBeenCalledWith({ fileIds: ["b"], name: "x", download: true });
    wrapper.unmount();
  });

  it("stays open when the merge is declined", async () => {
    const wrapper = mount(MergeFilesDialog, { attachTo: document.body });
    open(vi.fn().mockResolvedValue(false));
    await flushPromises();
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(useMergeFilesDialog().current.value).not.toBeNull();
    expect(wrapper.find("button.btn.primary").attributes("disabled")).toBeUndefined();
    wrapper.unmount();
  });
});
