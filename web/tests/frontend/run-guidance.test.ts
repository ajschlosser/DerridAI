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
        default_placeholder: "",
        instructions: "Exclude bibliography-only mentions.",
        look_for: ["Emmanuel Levinas", "Levinas"],
        required: false,
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
        default_placeholder: "",
        instructions: "",
        look_for: ["First "],
        required: false,
      },
    });
  });

  it("imports guidance for matching schema fields", async () => {
    const wrapper = mount(CorpusRunGuidance, {
      props: {
        fields: [
          { name: "persons", label: "People", group: "indexing" },
          { name: "work", label: "Work", group: "bibliography" },
        ],
        modelValue: {},
      },
    });
    const input = wrapper.find('input[type="file"]');
    const file = new File(
      [
        JSON.stringify({
          format: "derridai-run-guidance",
          version: 1,
          guidance: {
            persons: {
              default_placeholder: "",
              instructions: "Check attribution.",
              look_for: ["First Name Last Name"],
              required: false,
            },
            obsolete: { instructions: "Ignore this field.", look_for: [] },
          },
        }),
      ],
      "guidance.json",
      { type: "application/json" },
    );
    Object.defineProperty(input.element, "files", { value: [file] });
    await input.trigger("change");

    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual({
      persons: {
        default_placeholder: "",
        instructions: "Check attribution.",
        look_for: ["First Name Last Name"],
        required: false,
      },
    });
    expect(wrapper.find('[role="status"]').text()).toContain("imported");
  });
});
