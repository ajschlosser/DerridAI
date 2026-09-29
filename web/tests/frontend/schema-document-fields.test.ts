/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import SchemaDocumentFieldsPanel from "../../src/components/metadata-schemas/SchemaDocumentFieldsPanel.vue";
import {
  DOCUMENT_FIELD_NAMES,
  completeDocumentFields,
  type MetadataSchema,
} from "../../src/api/metadataSchemas";

const draft = (): MetadataSchema => ({
  format_version: 2,
  id: "s",
  name: "S",
  description: "",
  groups: [],
  fields: [],
  document_fields: completeDocumentFields([{ name: "translator", required_for: ["publication"] }]),
});

describe("document field policies", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("completes missing policies in canonical order and keeps given ones", () => {
    const policies = completeDocumentFields([
      { name: "translator", required_for: ["publication"] },
    ]);
    expect(policies.map((p) => p.name)).toEqual([...DOCUMENT_FIELD_NAMES]);
    expect(policies.find((p) => p.name === "translator")?.required_for).toEqual(["publication"]);
    expect(policies.find((p) => p.name === "document_author")?.required_for).toEqual([
      "evidence",
      "publication",
    ]);
  });

  it("edits requirements in the draft", async () => {
    const schema = draft();
    const wrapper = mount(SchemaDocumentFieldsPanel, { props: { draft: schema, readonly: false } });
    const authorRow = wrapper.findAll("tbody tr")[DOCUMENT_FIELD_NAMES.indexOf("document_author")];
    const [evidence] = authorRow.findAll('input[type="checkbox"]');
    await evidence.setValue(false);
    const author = schema.document_fields!.find((p) => p.name === "document_author")!;
    expect(author).toMatchObject({
      required_for: ["publication"],
    });
  });

  it("disables every control when read-only", () => {
    const wrapper = mount(SchemaDocumentFieldsPanel, { props: { draft: draft(), readonly: true } });
    expect(
      wrapper.findAll("select, input").every((el) => el.attributes("disabled") !== undefined),
    ).toBe(true);
  });
});
