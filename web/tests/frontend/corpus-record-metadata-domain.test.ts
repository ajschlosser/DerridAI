/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  editableRecordMetadata,
  evidenceCandidateFieldNames,
} from "../../src/features/corpus-builder/domain/recordMetadata";

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

  it("surfaces a custom schema evidence field without a product-specific allowlist", () => {
    const record = { custom_claim: "The supplement is constitutive." };
    const schema = {
      fields: [
        { name: "custom_claim", label: "Custom claim", evidence: true },
        { name: "internal_note", label: "Internal note", evidence: false },
      ],
    } as any;

    expect(evidenceCandidateFieldNames(record, schema)).toEqual(["custom_claim"]);
  });

  it("keeps canonical assertion evidence visible even without a compatibility projection", () => {
    const record = {
      field_assertions: {
        "schema.custom": [
          {
            assertion_id: "a1",
            field_id: "schema.custom",
            field_name: "custom_claim",
            value: "The supplement is constitutive.",
            derivation_method: "model",
            evaluation_status: "value_supported",
            authority_status: "unreviewed",
            value_status: "present",
            evidence: [{ block_id: "b-1" }],
          },
        ],
      },
      current_field_assertions: { "schema.custom": "a1" },
    };

    expect(evidenceCandidateFieldNames(record)).toEqual(["custom_claim"]);
  });

  it("keeps operational revision and runtime fields out of scholarly review", () => {
    const record = {
      speaker: "Derrida",
      text_revision_history: [{ at: "2026-09-25T00:00:00Z", source: "human" }],
      metadata_execution_ledger: { quotation: { status: "complete" } },
      field_assertions: {
        "legacy.utility": [
          {
            assertion_id: "utility-a1",
            field_id: "legacy.utility",
            field_name: "text_revision_history",
            value: [{ at: "2026-09-25T00:00:00Z" }],
            derivation_method: "imported",
            evaluation_status: "not_evaluated",
            authority_status: "unreviewed",
            value_status: "present",
          },
        ],
      },
      current_field_assertions: { "legacy.utility": "utility-a1" },
    };

    expect(editableRecordMetadata(record)).toEqual({ speaker: "Derrida" });
  });

  it("honors schema review visibility without relying on field names", () => {
    const record = {
      public_note: "review me",
      internal_note: "runtime detail",
    };
    const schema = {
      fields: [
        {
          name: "public_note",
          label: "Public note",
          role: "scholarly",
          review_visibility: "primary",
        },
        {
          name: "internal_note",
          label: "Internal note",
          role: "operational",
          review_visibility: "hidden",
        },
      ],
    } as any;

    expect(editableRecordMetadata(record, schema)).toEqual({ public_note: "review me" });
  });

});
