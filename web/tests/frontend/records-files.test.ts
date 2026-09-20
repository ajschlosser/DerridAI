/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  describeRecordsFile,
  recordsFileOrigin,
  recordsFileOriginDetail,
  serializableRecordsFile,
} from "../../src/domain/recordsFiles";

describe("records file origin", () => {
  it("treats a disk import as imported even when the content hash is present", () => {
    expect(recordsFileOrigin({content_hash: "abc"})).toBe("imported");
    expect(recordsFileOriginDetail({content_hash: "abc"})).toBe("");
  });

  it("keeps subset, merge, work-split, and Chroma export distinct", () => {
    expect(recordsFileOrigin({subset: {source: "active", source_label: "glas.jsonl"}})).toBe("subset");
    expect(recordsFileOriginDetail({subset: {source_label: "glas.jsonl"}})).toBe("glas.jsonl");
    expect(recordsFileOrigin({merged_from: ["a.jsonl", "b.jsonl"]})).toBe("merge");
    expect(recordsFileOriginDetail({merged_from: ["a.jsonl", "b.jsonl"]})).toBe("a.jsonl, b.jsonl");
    expect(
      recordsFileOrigin({derived_from: {type: "work_separation", source_file: "all.jsonl", work: "Glas"}}),
    ).toBe("work_split");
    expect(
      recordsFileOriginDetail({derived_from: {type: "work_separation", work: "Glas"}}),
    ).toBe("Glas");
    expect(recordsFileOrigin({imported_from_chroma: "derrida-primary"})).toBe("chroma");
  });

  it("does not invent an origin when provenance fields are missing after restore", () => {
    const described = describeRecordsFile({id: "f1", name: "old.jsonl", records: [{}, {}], dirty: [0], active: true});
    expect(described).toMatchObject({
      id: "f1",
      name: "old.jsonl",
      count: 2,
      dirty: 1,
      active: true,
      origin: "imported",
      origin_detail: "",
    });
  });

  it("round-trips provenance through the IndexedDB payload", () => {
    const saved = serializableRecordsFile({
      id: "subset-1",
      name: "subset.jsonl",
      records: [{record_id: "r1"}],
      dirty: new Set([0]),
      imported_at: "2026-09-20T12:00:00.000Z",
      subset: {source: "active", source_label: "glas.jsonl"},
      merged_from: null,
      derived_from: null,
      imported_from_chroma: null,
    });
    expect(saved.subset).toEqual({source: "active", source_label: "glas.jsonl"});
    expect(saved.dirty).toEqual([0]);
    expect(describeRecordsFile({...saved, dirty: saved.dirty}, "other").origin).toBe("subset");
  });
});
