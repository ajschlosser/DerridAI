import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusMetadataFieldEditor from "../../src/components/CorpusMetadataFieldEditor.vue";

const base = {
  field: "discourse_role",
  value: null,
  control: "enum" as const,
  options: ["assertion", "critique"],
};

describe("Blind review in the field editor", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("says the field is blind and shows no model value or prefill", () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: { ...base, status: { status: "unresolved", method: "llm", blind: true }, open: true },
    });
    expect(wrapper.text()).toMatch(/blind review/i);
    expect((wrapper.find("select").element as HTMLSelectElement).value).toBe("");
  });

  it("reveals the model's suggestion once the reviewer has decided", () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        ...base,
        value: "critique",
        status: { status: "human_confirmed" },
        revealed: "assertion",
      },
    });
    expect(wrapper.text()).toContain("The model had suggested: assertion");
    expect(wrapper.text()).not.toMatch(/blind review:/i);
  });
});
