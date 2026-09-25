/* Copyright 2026 Aaron John Schlosser, PhD. */
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
    expect(layout.overview.some((row) => row.kind === "field" && row.field === "document_author")).toBe(true);
    expect(layout.provenance.filter((row) => row.kind === "heading").map((row) => row.kind === "heading" && row.label)).toEqual([
      "Attribution",
      "Discourse",
    ]);
    expect(layout.indexing.filter((row) => row.kind === "field").map((row) => row.kind === "field" && row.field)).toEqual([
      "topics",
      "concepts",
      "persons",
      "works_referenced",
    ]);
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
    expect(unusedInspectorFields("indexing", defaultInspectorLayout().indexing)).toContain("institutions_referenced");
    expect(unusedInspectorFields("indexing", defaultInspectorLayout().indexing)).not.toContain("topics");
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
      layout.provenance.some(
        (row) => row.kind === "field" && row.field === "conceptual_tension",
      ),
    ).toBe(true);
    expect(
      unusedInspectorFields("provenance", [], record),
    ).toContain("conceptual_tension");

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
      restored.provenance.some(
        (row) => row.kind === "field" && row.field === "conceptual_tension",
      ),
    ).toBe(true);
  });

  it("groups stacked headings and the fields under them", () => {
    const grouped = groupInspectorRows(defaultInspectorLayout().overview);
    expect(grouped[0]?.heading).toBe("Record context");
    expect(grouped[0]?.fields).toContain("document_author");
    expect(grouped.at(-1)?.heading).toBe("Quotation provenance");
  });
});
