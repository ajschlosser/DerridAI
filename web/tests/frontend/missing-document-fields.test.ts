/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusMissingDocumentFields from "../../src/components/corpus-builder/CorpusMissingDocumentFields.vue";
import { completeDocumentFields } from "../../src/api/metadataSchemas";
import {
  missingRequiredDocumentFields,
  suppliedDocumentMetadata,
} from "../../src/domain/documentFields";

describe("required document fields detection missed", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("asks only for required fields that were not detected", () => {
    const schema = {
      document_fields: completeDocumentFields([
        { name: "translator", required_for: ["publication"] },
      ]),
    };
    const missing = missingRequiredDocumentFields(schema, {
      title: "De la grammatologie",
      document_author: "  ",
    });
    expect(missing.map((f) => f.name)).toEqual(["document_author", "translator"]);
    expect(
      missingRequiredDocumentFields(schema, { title: "T", document_author: "A", translator: "S" }),
    ).toEqual([]);
  });

  it("sends only trimmed, non-empty values for missing fields", () => {
    const missing = [{ name: "document_author", requiredFor: ["evidence" as const] }];
    expect(
      suppliedDocumentMetadata(missing, { document_author: " Jacques Derrida ", title: "stale" }),
    ).toEqual({ document_author: "Jacques Derrida" });
    expect(suppliedDocumentMetadata(missing, { document_author: "  " })).toEqual({});
  });

  it("renders nothing when every required field was detected", () => {
    const wrapper = mount(CorpusMissingDocumentFields, { props: { fields: [], modelValue: {} } });
    expect(wrapper.find("section").exists()).toBe(false);
  });

  it("edits the supplied values", async () => {
    const wrapper = mount(CorpusMissingDocumentFields, {
      props: {
        fields: [{ name: "document_author", requiredFor: ["evidence" as const] }],
        modelValue: {},
        "onUpdate:modelValue": (value: Record<string, string>) =>
          wrapper.setProps({ modelValue: value }),
      },
    });
    await wrapper.find("input").setValue("Jacques Derrida");
    expect(wrapper.props("modelValue")).toEqual({ document_author: "Jacques Derrida" });
  });
});
