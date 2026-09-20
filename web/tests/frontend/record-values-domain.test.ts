/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { cloneAuditValue, compareValues, computeRecordFingerprint, sameValue, sortRows, stableValue } from "../../src/domain/recordValues";

// The golden values below were produced by running the original functions from the legacy runtime.js.
describe("record values", () => {
  it("fingerprints records identically to the legacy runtime", () => {
    const records = [
      { record_id: "a", text: "x", topics: ["b", "a"], updates: [1], _chroma_id: "z", nested: { z: 1, a: 2 } },
      { a: 1 },
      { text: "héllo" },
    ];
    expect(records.map(computeRecordFingerprint)).toEqual(["c132b30a", "8b9e4511", "9fbe2c24"]);
  });

  it("ignores key order, update history and Chroma bookkeeping", () => {
    expect(stableValue({ b: 1, a: { d: 1, c: 2 }, updates: [1], _updates_count: 1, _chroma_id: "x" })).toEqual({ a: { c: 2, d: 1 }, b: 1 });
    expect(Object.keys(stableValue({ b: 1, a: 2 }) as object)).toEqual(["a", "b"]);
  });

  it("compares values identically to the legacy runtime", () => {
    const pairs: Array<[unknown, unknown]> = [[null, 1], [2, 10], ["a", "B"], [true, false], [["a", "b"], ["a"]], ["", "x"], ["10", "9"], ["item2", "item10"]];
    expect(pairs.map(([a, b]) => Math.sign(compareValues(a, b)))).toEqual([1, -1, -1, 1, 1, 1, 1, -1]);
  });

  it("sorts rows identically to the legacy runtime", () => {
    const rows = [
      { file: { name: "b" }, record: { n: 3 }, index: 0 },
      { file: { name: "a" }, record: { n: 3 }, index: 1 },
      { file: { name: "c" }, record: { n: 1 }, index: 2 },
      { file: { name: "d" }, record: {}, index: 3 },
    ];
    expect(sortRows(rows, { key: "n", dir: -1 }).map((r) => r.index)).toEqual([3, 1, 0, 2]);
    expect(sortRows(rows, { key: "__file", dir: 1 }).map((r) => r.index)).toEqual([1, 0, 2, 3]);
    expect(sortRows(rows, { dir: 1 })).toBe(rows);
  });

  it("clones and compares audit values", () => {
    expect(cloneAuditValue(undefined)).toBeNull();
    const original = { a: [1, 2] };
    const copy = cloneAuditValue(original) as typeof original;
    expect(copy).toEqual(original);
    expect(copy).not.toBe(original);
    expect(sameValue({ a: 1 }, { a: 1 })).toBe(true);
    expect(sameValue({ a: 1 }, { a: 2 })).toBe(false);
  });
});
