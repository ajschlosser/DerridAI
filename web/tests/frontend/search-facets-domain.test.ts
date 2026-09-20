/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { createSearchFacets } from "../../src/domain/searchFacets";
import { SEARCH_FACET_FIELDS } from "../../src/domain/runtimeConstants";

// The snapshots were verified to be identical to the original legacy runtime.js functions, over these
// records and filters, before they were recorded.
const tr = (k: string, f = "") => (k === "search.needs_review" ? "À revoir" : (f ?? k));
const label = (k: string) => `L(${k})`;
const display = (v: unknown) =>
  v == null || v === "" ? "—" : Array.isArray(v) ? v.join(", ") : String(v);
const pages = (r: { page_start?: unknown }) => `p${r.page_start ?? "-"}`;
const recordDbStatus = (_f: unknown, i: number) => ({ kind: i % 2 ? "synced" : "absent" });

const uid = () => "uid";
const state = {
  searchFacetFilters: { work: ["Of Grammatology"], topics: ["a"] } as Record<string, string[]>,
  dbSearchWhere: { speaker: "Derrida", empty: " " },
};
const dbSearchWhere = () =>
  Object.fromEntries(
    Object.entries(state.dbSearchWhere).filter(([, v]) => String(v ?? "").trim() !== ""),
  );
const recordFields = () => ["work", "text", "topics", "speaker", "extra", "updates"];
const filterOpsForField = (f: string) =>
  f === "year"
    ? [
        ["eq", "equals"],
        ["gte", "at least"],
      ]
    : [
        ["eq", "equals"],
        ["has", "contains"],
        ["empty", "is empty"],
      ];

const facets = createSearchFacets({
  tr,
  label,
  display,
  pages,
  recordDbStatus,
  recordFields,
  uid,
  dbSearchWhere,
  filterOpsForField,
  getSearchFacetFilters: () => state.searchFacetFilters,
} as never) as Record<string, (...a: unknown[]) => unknown>;

const file = { id: "f", name: "a.jsonl" };
const records = [
  {
    work: "Of Grammatology",
    document_author: "Derrida",
    topics: ["a", "b"],
    needs_review: true,
    speaker: "Derrida",
    year: 1967,
    page_start: 3,
    text: "hello world",
  },
  {
    work: "Glas",
    document_author: "Derrida",
    topics: "a;c",
    needs_review: false,
    year: 1974,
    text: "glass hello",
  },
  {
    work: "Glas",
    concepts: { x: "y", z: null },
    discourse_role: "",
    speaker: ["S1", null, "S2"],
    text: "none",
  },
  {},
];
const rows = records.map((record, index) => ({ file, record, index }));
const dbRecords = records.map((r) => ({ ...r }));

describe("search facets", () => {
  it("reads and displays facet values", () => {
    const out = records.map((r) =>
      SEARCH_FACET_FIELDS.map((f) => facets.searchFacetRawValues(r, f, rows[1])),
    );
    expect(out).toMatchSnapshot();
    expect(facets.searchFacetDisplay("needs_review", "true")).toBe("À revoir");
    expect(facets.searchFacetDisplay("work", "")).toBe("None");
  });
  it("counts and builds facets for workspace rows and database records", () => {
    expect(facets.buildSearchFacets(rows)).toMatchSnapshot();
    expect(facets.buildSearchFacets(dbRecords, { database: true })).toMatchSnapshot();
    expect(facets.searchSuggestions(rows)).toMatchSnapshot();
  });
  it("applies selected facets", () => {
    expect(rows.map((row) => facets.searchRowMatchesFacets(row))).toEqual([
      true,
      false,
      false,
      false,
    ]);
    expect(facets.searchFacetMatches(records[0], "topics", ["A"])).toBe(true);
  });
  it("describes filters and matches list filters", () => {
    expect(facets.searchFilterDescriptor({ field: "year", op: "gte", value: 1 })).toMatchSnapshot();
    expect(facets.dbSearchFilterDescriptors()).toMatchSnapshot();
    const filters = [{ field: "year", op: "gte", value: "1970" }];
    expect(rows.map((row) => facets.rowMatchesListFilters(row, filters))).toMatchSnapshot();
    expect(facets.searchMatchReasons(records[0], "hello")).toMatchSnapshot();
    expect(facets.searchSimilarity(1)).toBe(0.5);
  });
});
