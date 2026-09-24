/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { createRecordPresenters } from "../../src/domain/recordPresenters";

// The snapshots were verified to be identical to the original legacy runtime.js functions, over these
// inputs (and thousands of generated argument combinations), before they were recorded.
const tr = (_key: string, fallback = "") => fallback;
const trf = (_key: string, fallback: string, values: Record<string, unknown> = {}) =>
  Object.entries(values).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
    fallback,
  );
const presenters = createRecordPresenters({
  tr,
  trf,
  pages: (record: { page_start?: unknown }) => `p${record?.page_start ?? "-"}`,
  recordDbStatus: (_file: unknown, index: number) => ({
    kind: index % 2 ? "synced" : "absent",
    label: "L",
    title: "T",
  }),
  label: (key: string) => `L(${key})`,
  display: (value: unknown) => (value == null || value === "" ? "—" : String(value)),
  allAnnotations: () => [
    { work: "W", annotation: { note: "n" }, record: { record_id: "r" }, file: { name: "f" } },
  ],
  compareSearchIndex: () => [
    { key: "a", label: "Alpha rec", search: "alpha rec derrida", record: { text: "x" } },
    { key: "b", label: "Beta", search: "beta glas", record: {} },
  ],
} as never) as Record<string, (...args: unknown[]) => unknown>;

const rec = {
  record_id: "r1",
  work: "W",
  document_author: "A",
  year: 1967,
  page_start: 3,
  page_end: 5,
  text: "hello world text",
  topics: ["a", "b"],
  needs_review: true,
  updates: [{ field_name: "x" }],
};
const row = { file: { id: "f", name: "f.jsonl" }, record: rec, index: 1 };
const metric = {
  key: "k",
  title: "T",
  type: "pie",
  values: [
    { key: "a", value: 3, count: 2 },
    { key: "b", value: 1 },
  ],
  series: [{ key: "a", value: 3, count: 2 }],
  ranking: [{ key: "a", value: 2, count: 1 }],
  format: (v: number) => String(v),
  work: "W",
  valueLabel: "V",
  note: "n",
};
const pool: unknown[] = [
  undefined,
  null,
  "",
  "W",
  "topics",
  3,
  [],
  [row, { ...row, index: 0, record: { ...rec, work: "V", topics: "x;y" } }],
  rec,
  row,
  metric,
  [
    ["a", 3],
    ["b", 1],
  ],
  {
    annotation: {
      note: "n",
      quote: "q",
      tags: ["t"],
      created_at: "2026-01-01T00:00:00Z",
      author: "a",
    },
    record: rec,
    work: "W",
    file: row.file,
  },
  { selected: true },
  { key: "a", label: "Alpha", search: "alpha", record: rec },
];

describe("record presenters", () => {
  it("renders the pager", () => {
    expect(
      presenters.pager({ page: 2, pages: 5, start: 50, end: 100 }, 250, "list"),
    ).toMatchSnapshot();
    expect(presenters.pager({ page: 1, pages: 1, start: 0, end: 0 }, 0, "list")).toContain(
      "0 results",
    );
  });
  it("renders table cells", () => {
    expect(presenters.recordsListCell(row, "work", "hello")).toMatchSnapshot();
    expect(presenters.storeCellHtml(row.record, "text")).toMatchSnapshot();
  });
  it("previews RAG evidence", () => {
    expect(presenters.ragEvidencePreview(rec)).toMatchSnapshot();
  });
  it("builds dashboard and work insight fragments", () => {
    expect(presenters.dashboardMetricBody(metric)).toMatchSnapshot();
    expect(presenters.workInsightMetrics([row], "W")).toMatchSnapshot();
    expect(presenters.workInsightsPanelHtml([row], "W")).toMatchSnapshot();
  });
  it("localizes empty dashboard pie charts at render time", () => {
    const french = createRecordPresenters({
      tr: (key: string, fallback = "") =>
        key === "dashboard.no_data_yet" ? "aucune donnée pour le moment" : fallback,
      trf,
      pages: (record: { page_start?: unknown }) => `p${record?.page_start ?? "-"}`,
      recordDbStatus: () => ({ kind: "absent", label: "L", title: "T" }),
      label: (key: string) => `L(${key})`,
      display: (value: unknown) => (value == null || value === "" ? "—" : String(value)),
      allAnnotations: () => [],
      compareSearchIndex: () => [],
    } as never) as Record<string, (...args: unknown[]) => unknown>;
    const html = String(french.dashboardMetricBody({ type: "pie", title: "Share", values: [] }));
    expect(html).toContain("aucune donnée pour le moment");
    expect(html).not.toContain("no data yet");
  });
  it("searches compare options", () => {
    expect(presenters.searchRecordOptions("alpha")).toMatchSnapshot();
    expect(presenters.searchRecordOptions("")).toHaveLength(2);
  });
});
