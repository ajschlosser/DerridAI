// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusBoundarySliceDialog from "../../src/components/CorpusBoundarySliceDialog.vue";

const TEXT = "Alpha beta gamma delta epsilon.";

function mountDialog(props: Record<string, unknown> = {}) {
  return mount(CorpusBoundarySliceDialog, {
    props: { text: TEXT, canPrevious: true, canNext: true, ...props },
    global: {
      stubs: {
        UiDialog: { template: '<div><slot/><slot name="footer"/></div>' },
      },
    },
  });
}

async function select(wrapper: ReturnType<typeof mountDialog>, start: number, end: number) {
  const area = wrapper.get("textarea").element as HTMLTextAreaElement;
  area.setSelectionRange(start, end);
  await wrapper.get("textarea").trigger("mouseup");
}

describe("CorpusBoundarySliceDialog", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("splits at a caret", async () => {
    const wrapper = mountDialog();
    await select(wrapper, 11, 11);
    await wrapper.get("button.primary").trigger("click");
    expect(wrapper.emitted("split")?.[0]).toEqual([11]);
    expect(wrapper.emitted("create")).toBeUndefined();
  });

  it("creates a record from a selection and reports the join choices", async () => {
    const wrapper = mountDialog();
    await select(wrapper, 6, 16);
    await wrapper.get('input[name="slice-left"][value="merge_prior"]').setValue(true);
    await wrapper.get("button.primary").trigger("click");
    expect(wrapper.emitted("create")?.[0]).toEqual([6, 16, "merge_prior", "distinct"]);
  });

  it("refuses a selection of the whole record", async () => {
    const wrapper = mountDialog();
    await select(wrapper, 0, TEXT.length);
    expect(wrapper.get("button.primary").attributes("disabled")).toBeDefined();
  });

  it("does not offer joining a neighbour that does not exist", async () => {
    const wrapper = mountDialog({ canPrevious: false });
    await select(wrapper, 6, 16);
    expect(
      wrapper.get('input[name="slice-left"][value="merge_prior"]').attributes("disabled"),
    ).toBeDefined();
  });
});
