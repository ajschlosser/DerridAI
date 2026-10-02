// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import BulkFieldEditorDialog from "../../src/components/BulkFieldEditorDialog.vue";
import {
  closeBulkFieldEditorDialog,
  openBulkFieldEditorDialog,
  useBulkFieldEditorDialog,
} from "../../src/composables/bulkFieldEditorDialog";

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
  closeBulkFieldEditorDialog();
});

function open(over: Record<string, unknown> = {}) {
  const apply = vi.fn().mockResolvedValue(true);
  const inspect = vi.fn((_scope: string, field: string) =>
    field === "speaker"
      ? { targets: 3, distinct: 1, only: "Derrida" }
      : { targets: 3, distinct: 2, only: "x" },
  );
  openBulkFieldEditorDialog({
    title: "Bulk edit",
    fixedCount: null,
    defaultScope: "active",
    selectedCount: 0,
    activeCount: 3,
    currentWork: "",
    allCount: 9,
    fields: [
      { id: "speaker", label: "Speaker" },
      { id: "stance", label: "Stance" },
    ],
    inspect,
    apply,
    ...over,
  });
  return apply;
}

describe("BulkFieldEditorDialog", () => {
  it("prefills a value every record shares and clears it for a field where they differ", async () => {
    const wrapper = mount(BulkFieldEditorDialog, { attachTo: document.body });
    open();
    await flushPromises();
    const value = wrapper.find<HTMLTextAreaElement>("#bulkFieldValue");
    expect(value.element.value).toBe("Derrida");
    await wrapper.find("#bulkFieldName").setValue("stance");
    expect(value.element.value).toBe("");
    wrapper.unmount();
  });

  it("applies the chosen scope, field and text, then closes", async () => {
    const wrapper = mount(BulkFieldEditorDialog, { attachTo: document.body });
    const apply = open();
    await flushPromises();
    await wrapper.find("#bulkFieldScope").setValue("all");
    await wrapper.find("#bulkFieldValue").setValue("Husserl");
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(apply).toHaveBeenCalledWith({ scope: "all", field: "speaker", text: "Husserl" });
    expect(useBulkFieldEditorDialog().current.value).toBeNull();
    wrapper.unmount();
  });

  it("hides the scope picker for caller-fixed rows and stays open when declined", async () => {
    const wrapper = mount(BulkFieldEditorDialog, { attachTo: document.body });
    open({
      fixedCount: 4,
      defaultScope: "fixed",
      apply: vi.fn().mockResolvedValue(false),
    });
    await flushPromises();
    expect(wrapper.find("#bulkFieldScope").exists()).toBe(false);
    await wrapper.find("button.btn.primary").trigger("click");
    await flushPromises();
    expect(useBulkFieldEditorDialog().current.value).not.toBeNull();
    expect(wrapper.find("button.btn.primary").attributes("disabled")).toBeUndefined();
    wrapper.unmount();
  });
});
