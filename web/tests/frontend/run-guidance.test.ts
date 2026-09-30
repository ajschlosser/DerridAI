import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusRunGuidance from "../../src/components/CorpusRunGuidance.vue";

describe("Corpus run guidance", () => {
  beforeEach(() => setActivePinia(createPinia()));

  const persons = { name: "persons", label: "People", group: "indexing" };

  it("emits field-specific instructions and search cues as chips", async () => {
    const wrapper = mount(CorpusRunGuidance, { props: { fields: [persons], modelValue: {} } });
    await wrapper.find("textarea").setValue("Exclude bibliography-only mentions.");
    await wrapper.setProps({
      modelValue: wrapper.emitted("update:modelValue")?.at(-1)?.[0] as never,
    });
    const cues = wrapper.find("#run-guidance-terms-persons");
    await cues.setValue("Emmanuel Levinas");
    await cues.trigger("keydown", { key: "Enter" });
    await wrapper.setProps({
      modelValue: wrapper.emitted("update:modelValue")?.at(-1)?.[0] as never,
    });
    await cues.setValue("Levinas, levinas; Lévinas");
    await cues.trigger("keydown", { key: "Enter" });

    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual({
      persons: {
        default_placeholder: "",
        instructions: "Exclude bibliography-only mentions.",
        look_for: ["Emmanuel Levinas", "Levinas", "Lévinas"],
        required: false,
      },
    });
  });

  it("removes a cue and toggles a required value with a fallback placeholder", async () => {
    const wrapper = mount(CorpusRunGuidance, {
      props: {
        fields: [persons],
        modelValue: { persons: { instructions: "", look_for: ["A", "B"], required: false } },
      },
    });
    await wrapper.find(".rg-chip button").trigger("click");
    expect((wrapper.emitted("update:modelValue")?.at(-1)?.[0] as any).persons.look_for).toEqual([
      "B",
    ]);
    await wrapper.find('[role="switch"]').trigger("click");
    const last = (wrapper.emitted("update:modelValue")?.at(-1)?.[0] as any).persons;
    expect(last.required).toBe(true);
    expect(last.default_placeholder).toBeTruthy();
  });

  it("filters fields by search text and shows configured state", async () => {
    const wrapper = mount(CorpusRunGuidance, {
      props: {
        fields: [persons, { name: "work", label: "Work", group: "bibliography" }],
        modelValue: { work: { instructions: "Use title page", look_for: [] } },
      },
    });
    expect(wrapper.findAll(".rg-row")).toHaveLength(2);
    await wrapper.find('input[type="search"]').setValue("peo");
    expect(wrapper.findAll(".rg-row")).toHaveLength(1);
    await wrapper.find('input[type="search"]').setValue("");
    await wrapper.findAll(".rg-filters button")[1].trigger("click");
    expect(wrapper.findAll(".rg-row").map((row) => row.text())).toEqual([
      expect.stringContaining("Work"),
    ]);
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
