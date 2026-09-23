import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusRunGuidance from "../../src/components/CorpusRunGuidance.vue";

describe("Corpus run guidance", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("emits field-specific instructions and whole-line search cues", async () => {
    const wrapper = mount(CorpusRunGuidance, {
      props: {
        fields: [{ name: "persons", label: "People", group: "indexing" }],
        modelValue: {},
      },
    });
    const textareas = wrapper.findAll("textarea");
    await textareas[0].setValue("Exclude bibliography-only mentions.");
    const afterInstruction = wrapper.emitted("update:modelValue")?.at(-1)?.[0] as Record<
      string,
      unknown
    >;
    await wrapper.setProps({ modelValue: afterInstruction });
    await wrapper.findAll("textarea")[1].setValue("Emmanuel Levinas\nLevinas\n");

    const updates = wrapper.emitted("update:modelValue");
    expect(updates).toBeTruthy();
    expect(updates?.at(-1)?.[0]).toEqual({
      persons: {
        instructions: "Exclude bibliography-only mentions.",
        look_for: ["Emmanuel Levinas", "Levinas"],
      },
    });
  });

  it("keeps spaces in a phrase while it is being typed", async () => {
    const wrapper = mount(CorpusRunGuidance, {
      props: {
        fields: [{ name: "persons", label: "People", group: "indexing" }],
        modelValue: {},
      },
    });

    await wrapper.findAll("textarea")[1].setValue("First ");

    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual({
      persons: {
        instructions: "",
        look_for: ["First "],
      },
    });
  });
});
