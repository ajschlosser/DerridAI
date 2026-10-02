// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import OcrCleanupDialog from "../../src/components/OcrCleanupDialog.vue";
import {
  closeOcrCleanupDialog,
  openOcrCleanupDialog,
  useOcrCleanupDialog,
} from "../../src/composables/ocrCleanupDialog";

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
  closeOcrCleanupDialog();
});

function open(over: Record<string, unknown> = {}) {
  const choose = vi.fn().mockResolvedValue(undefined);
  openOcrCleanupDialog({
    active: { name: "a.jsonl", recordCount: 2 },
    selectedCount: 0,
    reviewCount: 1,
    allCount: 5,
    fileCount: 2,
    choose,
    ...over,
  });
  return choose;
}

describe("OcrCleanupDialog", () => {
  it("closes first, then reports the chosen scope", async () => {
    const wrapper = mount(OcrCleanupDialog, { attachTo: document.body });
    const choose = open();
    await flushPromises();
    await wrapper.findAll(".scope-card")[2].trigger("click");
    await flushPromises();
    expect(choose).toHaveBeenCalledWith("review");
    expect(useOcrCleanupDialog().current.value).toBeNull();
    wrapper.unmount();
  });

  it("disables the scopes that have nothing to clean", async () => {
    const wrapper = mount(OcrCleanupDialog, { attachTo: document.body });
    const choose = open({ active: null });
    await flushPromises();
    const cards = wrapper.findAll(".scope-card");
    expect(cards[0].attributes("disabled")).toBeDefined();
    expect(cards[1].attributes("disabled")).toBeDefined();
    expect(cards[3].attributes("disabled")).toBeUndefined();
    await cards[0].trigger("click");
    expect(choose).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
