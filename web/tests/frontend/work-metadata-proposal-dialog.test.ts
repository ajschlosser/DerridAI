// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import WorkMetadataProposalDialog from "../../src/components/WorkMetadataProposalDialog.vue";
import {
  closeWorkMetadataProposalDialog,
  openWorkMetadataProposalDialog,
  useWorkMetadataProposalDialog,
  type WorkMetadataProposalEntry,
} from "../../src/composables/workMetadataProposalDialog";

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
  closeWorkMetadataProposalDialog();
});

const entry = (field: string, proposed: string): WorkMetadataProposalEntry => ({
  work: "W",
  recordCount: 3,
  fieldLabel: field,
  current: "old",
  proposed,
  rationale: "",
  confidence: 0.5,
});

function open(apply = vi.fn().mockResolvedValue(true)) {
  openWorkMetadataProposalDialog({
    jobLabel: "job",
    entries: [entry("Publisher", "P"), entry("Year", "1976")],
    unmatched: [{ work: "X", message: "" }],
    apply,
  });
  return apply;
}

describe("WorkMetadataProposalDialog", () => {
  it("applies every proposal by default, with edited text, then closes", async () => {
    const wrapper = mount(WorkMetadataProposalDialog, { attachTo: document.body });
    const apply = open();
    await flushPromises();
    await wrapper.findAll("textarea")[1].setValue("1977");
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(apply).toHaveBeenCalledWith([
      { index: 0, value: "P" },
      { index: 1, value: "1977" },
    ]);
    expect(useWorkMetadataProposalDialog().current.value).toBeNull();
    wrapper.unmount();
  });

  it("sends only the ticked rows and does not apply when none are ticked", async () => {
    const wrapper = mount(WorkMetadataProposalDialog, { attachTo: document.body });
    const apply = open();
    await flushPromises();
    await wrapper.findAll("input[type=checkbox]")[0].setValue(false);
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(apply).toHaveBeenCalledWith([{ index: 1, value: "1976" }]);

    open(apply.mockClear());
    await flushPromises();
    const clear = wrapper.findAll(".work-proposal-toolbar button")[1];
    await clear.trigger("click");
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(apply).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("stays open when apply reports a validation problem", async () => {
    const wrapper = mount(WorkMetadataProposalDialog, { attachTo: document.body });
    open(vi.fn().mockResolvedValue(false));
    await flushPromises();
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(useWorkMetadataProposalDialog().current.value).not.toBeNull();
    expect(wrapper.find("button.btn.primary").attributes("disabled")).toBeUndefined();
    wrapper.unmount();
  });
});
