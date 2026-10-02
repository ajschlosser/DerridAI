// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { beforeAll, describe, expect, it, vi } from "vitest";
import RemoveWorkDialog from "../../src/components/RemoveWorkDialog.vue";
import { useMessageDialog } from "../../src/composables/messageDialog";
import {
  closeRemoveWorkDialog,
  openRemoveWorkDialog,
} from "../../src/composables/removeWorkDialog";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

const files = [
  { id: "a", name: "a.jsonl", count: 2 },
  { id: "b", name: "b.jsonl", count: 1 },
];

describe("RemoveWorkDialog", () => {
  it("passes the checked files and vector-store choice to the caller, then closes", async () => {
    const confirm = vi.fn().mockResolvedValue(undefined);
    const wrapper = mount(RemoveWorkDialog, { attachTo: document.body });
    openRemoveWorkDialog({ work: "W", files, dbStore: "store", confirm });
    await flushPromises();
    const boxes = wrapper.findAll("input[type=checkbox]");
    expect(boxes).toHaveLength(3);
    await boxes[1].setValue(false);
    await boxes[2].setValue(true);
    await wrapper.find("button.danger").trigger("click");
    await flushPromises();
    expect(confirm).toHaveBeenCalledWith({ fileIds: ["a"], removeDb: true });
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });

  it("disables the vector-store option when none is selected and ignores it", async () => {
    const confirm = vi.fn().mockResolvedValue(undefined);
    const wrapper = mount(RemoveWorkDialog, { attachTo: document.body });
    openRemoveWorkDialog({ work: "W", files, dbStore: "", confirm });
    await flushPromises();
    expect(wrapper.findAll("input[type=checkbox]")[2].attributes("disabled")).toBeDefined();
    await wrapper.find("button.danger").trigger("click");
    await flushPromises();
    expect(confirm).toHaveBeenCalledWith({ fileIds: ["a", "b"], removeDb: false });
    wrapper.unmount();
  });

  it("does not call the caller when nothing is selected", async () => {
    const confirm = vi.fn();
    const wrapper = mount(RemoveWorkDialog, { attachTo: document.body });
    openRemoveWorkDialog({ work: "W", files, dbStore: "", confirm });
    await flushPromises();
    for (const box of wrapper.findAll("input[type=checkbox]:not(:disabled)"))
      await box.setValue(false);
    await wrapper.find("button.danger").trigger("click");
    expect(confirm).not.toHaveBeenCalled();
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    closeRemoveWorkDialog();
    wrapper.unmount();
  });

  it("stays open and reports the error when the removal fails", async () => {
    const confirm = vi.fn().mockRejectedValue(new Error("server said no"));
    const wrapper = mount(RemoveWorkDialog, { attachTo: document.body });
    openRemoveWorkDialog({ work: "W", files, dbStore: "", confirm });
    await flushPromises();
    await wrapper.find("button.danger").trigger("click");
    await flushPromises();
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    expect(wrapper.find("button.danger").attributes("disabled")).toBeUndefined();
    expect(useMessageDialog().queue.value[0]?.message).toBe("server said no");
    closeRemoveWorkDialog();
    wrapper.unmount();
  });
});
