import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import UiTagPicker from "../../src/components/ui/UiTagPicker.vue";

describe("UiTagPicker", () => {
  it("filters options without replacing selected values and emits selections", async () => {
    const wrapper = mount(UiTagPicker, {
      props: {
        modelValue: ["NOUN"],
        options: ["NOUN", "PROPN", "PRON", "VERB"],
        label: "POS tags",
      },
      attachTo: document.body,
    });

    const input = wrapper.get("input");
    await input.setValue("prop");

    expect(wrapper.text()).toContain("NOUN");
    expect(wrapper.text()).toContain("PROPN");
    expect(wrapper.text()).not.toContain("VERB");

    await wrapper.get('[role="option"]').trigger("mousedown");
    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual(["NOUN", "PROPN"]);

    wrapper.unmount();
  });

  it("removes a selected tag independently of the search query", async () => {
    const wrapper = mount(UiTagPicker, {
      props: {
        modelValue: ["PERSON", "ORG"],
        options: ["PERSON", "ORG", "WORK_OF_ART"],
        label: "NER tags",
      },
    });

    const remove = wrapper.get('button[aria-label="Remove PERSON"]');
    await remove.trigger("click");

    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual(["ORG"]);
  });
});
