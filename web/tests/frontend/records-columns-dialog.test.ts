/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import { nextTick, ref } from "vue";
import RecordsColumnsDialog from "../../src/components/records/RecordsColumnsDialog.vue";
import { useI18nStore } from "../../src/stores/i18n";

const available = [
  {key: "work", label: "Work"},
  {key: "text", label: "Text"},
  {key: "speaker", label: "Speaker"},
];

describe("RecordsColumnsDialog", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().languages = [{code: "en-US", name: "English", flag: ""}] as never;
  });

  it("adds a hidden field and reorders visible columns", async () => {
    const selected = ref(["work", "text"]);
    const wrapper = mount(RecordsColumnsDialog, {
      attachTo: document.body,
      props: {
        available,
        modelValue: selected.value,
        "onUpdate:modelValue": (keys: string[]) => {
          selected.value = keys;
          wrapper.setProps({modelValue: keys});
        },
      },
    });
    (wrapper.vm as {open: () => void}).open();
    await nextTick();
    await wrapper.get(".records-columns-add").trigger("click");
    expect(selected.value).toEqual(["work", "text", "speaker"]);
    await wrapper.setProps({modelValue: selected.value});
    await wrapper.get('[aria-label="Move Speaker up"]').trigger("click");
    expect(selected.value).toEqual(["work", "speaker", "text"]);
    wrapper.unmount();
  });

  it("keeps at least one visible column", async () => {
    const wrapper = mount(RecordsColumnsDialog, {
      attachTo: document.body,
      props: {available, modelValue: ["work"]},
    });
    (wrapper.vm as {open: () => void}).open();
    await flushPromises();
    expect(wrapper.get('[aria-label="Hide Work"]').attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });
});
