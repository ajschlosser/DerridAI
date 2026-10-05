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
  defaultInspectorLayout,
  groupInspectorRows,
  moveInspectorRow,
  normalizeInspectorLayout,
  unusedInspectorFields,
} from "../../src/domain/inspectorLayout";

describe("inspector layout", () => {
  it("keeps default overview, provenance, and indexing rows", () => {
    const layout = defaultInspectorLayout();
    expect(
      layout.overview.some((row) => row.kind === "field" && row.field === "document_author"),
    ).toBe(true);
    expect(
      layout.provenance
        .filter((row) => row.kind === "heading")
        .map((row) => row.kind === "heading" && row.label),
    ).toEqual(["Attribution", "Discourse"]);
    expect(
      layout.indexing
        .filter((row) => row.kind === "field")
        .map((row) => row.kind === "field" && row.field),
    ).toEqual(["topics", "concepts", "persons", "works_referenced"]);
  });

  it("reorders stacked heading and field rows", () => {
    const rows = defaultInspectorLayout().indexing;
    const moved = moveInspectorRow(rows, 1, 3);
    expect(moved[3].kind === "field" && moved[3].field).toBe("topics");
  });

  it("drops unknown fields and duplicate keys when restoring a saved layout", () => {
    const layout = normalizeInspectorLayout({
      overview: [
        { kind: "heading", label: "Custom" },
        { kind: "field", field: "year" },
        { kind: "field", field: "year" },
        { kind: "field", field: "not_a_field" },
      ],
    });
    expect(layout.overview).toHaveLength(2);
    expect(layout.overview[0]).toMatchObject({ kind: "heading", label: "Custom" });
    expect(layout.overview[1]).toMatchObject({ kind: "field", field: "year" });
  });

  it("lists catalog fields that are not yet in the tab", () => {
    expect(unusedInspectorFields("indexing", defaultInspectorLayout().indexing)).toContain(
      "institutions_referenced",
    );
    expect(unusedInspectorFields("indexing", defaultInspectorLayout().indexing)).not.toContain(
      "topics",
    );
  });

  it("discovers custom assertion fields without adding them to the hard-coded catalog", () => {
    const record = {
      field_assertions: {
        "field-conceptual-tension": [
          {
            assertion_id: "a1",
            field_id: "field-conceptual-tension",
            field_name: "conceptual_tension",
            value: "hospitality / sovereignty",
            derivation_method: "model",
            evaluation_status: "value_supported",
            authority_status: "human_confirmed",
            value_status: "present",
          },
        ],
      },
      current_field_assertions: { "field-conceptual-tension": "a1" },
    };
    const layout = defaultInspectorLayout(record);
    expect(
      layout.provenance.some((row) => row.kind === "field" && row.field === "conceptual_tension"),
    ).toBe(true);
    expect(unusedInspectorFields("provenance", [], record)).toContain("conceptual_tension");

    const restored = normalizeInspectorLayout(
      {
        provenance: [
          { kind: "heading", label: "Project fields" },
          { kind: "field", field: "conceptual_tension" },
        ],
      },
      record,
    );
    expect(
      restored.provenance.some((row) => row.kind === "field" && row.field === "conceptual_tension"),
    ).toBe(true);
  });

  it("derives schema-backed inspector tabs and headings without built-in scholarly names", () => {
    const schema = {
      id: "custom",
      groups: [
        { key: "analysis", label: "Analysis" },
        { key: "references", label: "References" },
      ],
      fields: [
        {
          field_id: "field-tension",
          name: "conceptual_tension",
          semantic_compatibility_id: null,
          label: "Conceptual tension",
          type: "text",
          group: "analysis",
          role: "scholarly",
          scope: "record",
          review: true,
          evidence: false,
          assess: false,
          values: [],
          strict: false,
          instruction: "",
          definitions_heading: "",
          retrieval_profile: {
            enabled: true,
            max_items: 6,
            min_similarity: 0,
            include_corrections: true,
            include_confirmed_absence: true,
          },
          pos_tags: [],
          ner_tags: [],
        },
        {
          field_id: "field-people",
          name: "people_index",
          semantic_compatibility_id: "derridai.indexing.persons",
          label: "People",
          type: "list",
          group: "references",
          role: "scholarly",
          scope: "record",
          review: false,
          evidence: false,
          assess: false,
          values: [],
          strict: false,
          instruction: "",
          definitions_heading: "",
          retrieval_profile: {
            enabled: true,
            max_items: 6,
            min_similarity: 0,
            include_corrections: true,
            include_confirmed_absence: true,
          },
          pos_tags: [],
          ner_tags: [],
        },
        {
          field_id: "field-corpus-note",
          name: "corpus_note",
          semantic_compatibility_id: null,
          label: "Corpus note",
          type: "text",
          group: "analysis",
          role: "scholarly",
          scope: "corpus",
          review: false,
          evidence: false,
          assess: false,
          values: [],
          strict: false,
          instruction: "",
          definitions_heading: "",
          retrieval_profile: {
            enabled: true,
            max_items: 6,
            min_similarity: 0,
            include_corrections: true,
            include_confirmed_absence: true,
          },
          pos_tags: [],
          ner_tags: [],
        },
      ],
    };

    const layout = defaultInspectorLayout({}, schema as never);
    expect(
      layout.provenance.some((row) => row.kind === "field" && row.field === "conceptual_tension"),
    ).toBe(true);
    expect(
      layout.indexing.some((row) => row.kind === "field" && row.field === "people_index"),
    ).toBe(true);
    expect(
      Object.values(layout)
        .flat()
        .some((row) => row.kind === "field" && row.field === "corpus_note"),
    ).toBe(false);
    expect(
      Object.values(layout)
        .flat()
        .some((row) => row.kind === "field" && row.field === "speaker"),
    ).toBe(false);
    expect(
      layout.provenance
        .filter((row) => row.kind === "heading")
        .map((row) => row.kind === "heading" && row.label),
    ).toContain("Analysis");
  });

  it("groups stacked headings and the fields under them", () => {
    const grouped = groupInspectorRows(defaultInspectorLayout().overview);
    expect(grouped[0]?.heading).toBe("Record context");
    expect(grouped[0]?.fields).toContain("document_author");
    expect(grouped.at(-1)?.heading).toBe("Quotation provenance");
  });
});
