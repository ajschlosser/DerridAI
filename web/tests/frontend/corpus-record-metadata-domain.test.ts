/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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

  it("edits a repeatable field as one associated value instead of parallel member fields", () => {
    const quotations = [
      {
        instance_id: "quote:1",
        quoted_speaker: "Levinas",
        quoted_addressee: "Derrida",
      },
    ];
    const schema = {
      fields: [
        {
          name: "quotations",
          group: "quotation",
          label: "Quotations",
          type: "repeatable",
          members: [
            { name: "quoted_speaker", label: "Quoted speaker" },
            { name: "quoted_addressee", label: "Quoted addressee" },
          ],
        },
      ],
      groups: [{ key: "quotation" }],
    } as any;

    expect(editableRecordMetadata({ quotations }, schema)).toEqual({ quotations });
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
