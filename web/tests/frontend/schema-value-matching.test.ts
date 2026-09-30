/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import { reactive } from "vue";
import { blankField, type SchemaField } from "../../src/api/metadataSchemas";
import SchemaFieldForm from "../../src/components/metadata-schemas/SchemaFieldForm.vue";

function mountForm(over: Partial<SchemaField> = {}) {
  const field = reactive<SchemaField>({
    ...blankField("indexing"),
    name: "people",
    label: "People",
    ...over,
  });
  const wrapper = mount(SchemaFieldForm, { props: { field, groupKeys: ["indexing"] } });
  const fieldset = () => wrapper.find("fieldset.value-matching");
  return { field, wrapper, fieldset };
}

describe("Schema field value matching", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("follows DerridAI's default until a mode is chosen, and can return to it", async () => {
    const { field, fieldset } = mountForm({ type: "list" });
    const select = fieldset().find("select");
    expect((select.element as HTMLSelectElement).value).toBe("");
    expect(fieldset().text()).toContain("DerridAI's policy for this field's meaning");
    expect(fieldset().find("input").exists()).toBe(false);

    await select.setValue("entity_name");
    expect(field.equivalence_profile).toEqual({
      mode: "entity_name",
      collection_semantics: "set",
      identity_kind: null,
    });
    expect(fieldset().text()).toContain("J. P. Dingus");

    await select.setValue("");
    expect(field.equivalence_profile).toBeNull();
  });

  it("offers list order only for lists and trims an identity kind", async () => {
    const list = mountForm({
      type: "list",
      equivalence_profile: {
        mode: "lexical_phrase",
        collection_semantics: "set",
        identity_kind: null,
      },
    });
    const selects = list.fieldset().findAll("select");
    expect(selects).toHaveLength(2);
    await selects[1].setValue("ordered");
    expect(list.field.equivalence_profile?.collection_semantics).toBe("ordered");
    const kind = list.fieldset().find("input");
    await kind.setValue(" motif ");
    await kind.trigger("change");
    expect(list.field.equivalence_profile?.identity_kind).toBe("motif");
    await kind.setValue("");
    await kind.trigger("change");
    expect(list.field.equivalence_profile?.identity_kind).toBeNull();
    // The note is tied to the choice for assistive technology.
    const describedBy = list.fieldset().find("select").attributes("aria-describedby");
    expect(list.fieldset().find(`#${describedBy}`).text()).toContain("spaCy");

    const scalar = mountForm({
      type: "text",
      equivalence_profile: { mode: "text", collection_semantics: "set", identity_kind: null },
    });
    expect(scalar.fieldset().findAll("select")).toHaveLength(1);
  });
});
