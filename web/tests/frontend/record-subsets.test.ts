/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { createRecordSubsets, subsetFileName } from "../../src/domain/recordSubsets";

function setup() {
  const state = {
    activeFileId: "f1",
    files: [
      {
        id: "f1",
        name: "glas.jsonl",
        records: [
          { record_id: "glas-1", work: "Glas", _audit: [{ at: "t" }] },
          { record_id: "glas-2", work: "Glas (tr.)" },
        ],
      },
      { id: "f2", name: "margins.jsonl", records: [{ record_id: "m-1", work: "Margins" }] },
    ],
  };
  const deps = {
    state,
    cloneAuditValue: <T>(value: T) => structuredClone(value),
    downloadBlob: vi.fn(),
    label: (field: string) => `Label ${field}`,
    navigateTo: vi.fn(),
    persistFileNow: vi.fn(async () => undefined),
    uid: () => "new-file",
  };
  return { state, deps, subsets: createRecordSubsets(deps) };
}
const glasOnly = [
  {
    type: "rule" as const,
    join: "AND" as const,
    rule: { field: "work", operator: "equals", value: "glas" },
  },
];

describe("record subsets", () => {
  it("lists sources and fields without internal fields", () => {
    const { subsets } = setup();
    expect(subsets.subsetSources().map((source) => [source.id, source.count])).toEqual([
      ["active", 2],
      ["all", 3],
      ["f1", 2],
      ["f2", 1],
    ]);
    expect(subsets.subsetFields()).toEqual([
      { key: "record_id", label: "Label record_id" },
      { key: "work", label: "Label work" },
    ]);
    expect(subsets.defaultSubsetName()).toBe("glas-subset.jsonl");
  });

  it("creates a file of copies that keep record identity and records its provenance", async () => {
    const { state, deps, subsets } = setup();
    const created = await subsets.createSubsetFile({
      name: "only-glas",
      source: "active",
      expression: glasOnly,
      caseSensitive: false,
      download: true,
    });
    expect(created).toEqual({ name: "only-glas.jsonl", count: 1 });
    const file = state.files[2] as Record<string, any>;
    expect(file.records).toEqual([{ record_id: "glas-1", work: "Glas", _audit: [{ at: "t" }] }]);
    expect(file.records[0]).not.toBe(state.files[0].records[0]);
    // "active" is resolved to the file it meant at creation time.
    expect(file.subset).toMatchObject({
      source: "f1",
      source_label: "glas.jsonl",
      logic: "grouped_boolean_v2",
      case_sensitive: false,
      expression: glasOnly,
    });
    expect(state.activeFileId).toBe("new-file");
    expect(deps.persistFileNow).toHaveBeenCalledWith(file);
    expect(deps.downloadBlob).toHaveBeenCalledWith(expect.any(Blob), "only-glas.jsonl");
    expect(deps.navigateTo).toHaveBeenCalledWith("list", { fileId: "new-file" });
  });

  it("creates nothing when no record matches", async () => {
    const { state, subsets } = setup();
    const created = await subsets.createSubsetFile({
      name: "x",
      source: "f2",
      expression: glasOnly,
      caseSensitive: false,
      download: false,
    });
    expect(created.count).toBe(0);
    expect(state.files).toHaveLength(2);
  });

  it("names the file with a .jsonl extension", () => {
    expect(subsetFileName("  ")).toBe("subset.jsonl");
    expect(subsetFileName("a.JSONL")).toBe("a.JSONL");
    expect(subsetFileName("a")).toBe("a.jsonl");
  });
});
