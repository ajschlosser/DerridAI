/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { editableRecordMetadata } from "../../src/features/corpus-builder/domain/recordMetadata";

describe("Corpus Builder editable metadata packet", () => {
  it("includes schema-defined and canonical assertion fields without transporting operational state", () => {
    const record = {
      record_id: "r1",
      text: "source text",
      speaker: "Derrida",
      custom_field: "custom",
      build_id: "b1",
      metadata_field_status: { speaker: { status: "human_confirmed" } },
      field_assertions: {
        "schema.custom": [
          {
            assertion_id: "a1",
            field_id: "schema.custom",
            field_name: "custom_field",
            value: "custom",
            derivation_method: "model",
            evaluation_status: "value_supported",
            authority_status: "unreviewed",
            value_status: "present",
          },
        ],
      },
      current_field_assertions: { "schema.custom": "a1" },
    };
    const schema = {
      id: "s1",
      name: "Schema",
      version: "1",
      fields: [{ name: "speaker", label: "Speaker" }],
      groups: [],
    } as any;

    expect(editableRecordMetadata(record, schema)).toEqual({
      speaker: "Derrida",
      custom_field: "custom",
    });
  });

  it("retains the locked structural fields as explicit editable policy", () => {
    expect(
      editableRecordMetadata({
        region_type: "main_text",
        primary_text: true,
        discourse_role: "argument",
      }),
    ).toEqual({
      region_type: "main_text",
      primary_text: true,
      discourse_role: "argument",
    });
  });
});
