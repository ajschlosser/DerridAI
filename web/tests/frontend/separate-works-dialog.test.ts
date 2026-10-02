// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { beforeAll, describe, expect, it, vi } from "vitest";
import SeparateWorksDialog from "../../src/components/SeparateWorksDialog.vue";
import { useMessageDialog } from "../../src/composables/messageDialog";
import {
  closeSeparateWorksDialog,
  openSeparateWorksDialog,
} from "../../src/composables/separateWorksDialog";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

const sources = [
  {
    id: "a",
    name: "a.jsonl",
    recordCount: 3,
    groups: [
      { work: "One", count: 2, defaultChecked: true },
      { work: "Untitled", count: 1, defaultChecked: false },
    ],
  },
  {
    id: "b",
    name: "b.jsonl",
    recordCount: 2,
    groups: [{ work: "Two", count: 2, defaultChecked: true }],
  },
];

describe("SeparateWorksDialog", () => {
  it("leaves untitled groups unchecked and submits the chosen works for the chosen source", async () => {
    const confirm = vi.fn().mockResolvedValue(undefined);
    const wrapper = mount(SeparateWorksDialog, { attachTo: document.body });
    openSeparateWorksDialog({ sources, confirm });
    await flushPromises();
    let boxes = wrapper.findAll(".separate-work-row input");
    expect(boxes.map((box) => (box.element as HTMLInputElement).checked)).toEqual([true, false]);
    await wrapper.find("select").setValue("b");
    boxes = wrapper.findAll(".separate-work-row input");
    expect(boxes).toHaveLength(1);
    await wrapper.find(".check-item input").setValue(true);
    await wrapper.find("button.primary").trigger("click");
    await flushPromises();
    expect(confirm).toHaveBeenCalledWith({ fileId: "b", works: ["Two"], removeFromSource: true });
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });

  it("does nothing when no work is selected", async () => {
    const confirm = vi.fn();
    const wrapper = mount(SeparateWorksDialog, { attachTo: document.body });
    openSeparateWorksDialog({ sources, confirm });
    await flushPromises();
    await wrapper.find(".separate-work-row input").setValue(false);
    await wrapper.find("button.primary").trigger("click");
    expect(confirm).not.toHaveBeenCalled();
    closeSeparateWorksDialog();
    wrapper.unmount();
  });

  it("stays open and reports the error when the split fails", async () => {
    const confirm = vi.fn().mockRejectedValue(new Error("disk full"));
    const wrapper = mount(SeparateWorksDialog, { attachTo: document.body });
    openSeparateWorksDialog({ sources, confirm });
    await flushPromises();
    await wrapper.find("button.primary").trigger("click");
    await flushPromises();
    expect(wrapper.find("dialog").attributes("open")).toBeDefined();
    expect(useMessageDialog().queue.value[0]?.message).toBe("disk full");
    closeSeparateWorksDialog();
    wrapper.unmount();
  });
});
