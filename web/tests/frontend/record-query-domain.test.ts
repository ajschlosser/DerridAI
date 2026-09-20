/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  countOccurrences,
  flattenValueList,
  parseJsonl,
  subsetRuleMatches,
  subsetValueText,
  valueMatches,
} from "../../src/domain/recordQuery";

// These behaviors were checked against the original legacy runtime.js functions across a wide input matrix.
describe("record query helpers", () => {
  it("parses JSONL and JSON arrays", () => {
    expect(parseJsonl("")).toEqual({ records: [], errors: [] });
    expect(parseJsonl('{"a":1}\n\n{"b":2}')).toEqual({ records: [{ a: 1 }, { b: 2 }], errors: [] });
    expect(parseJsonl('[{"a":1},2]')).toEqual({
      records: [{ a: 1 }],
      errors: ["Item 2: not an object"],
    });
    expect(parseJsonl('{"a":1}\n[1]').errors).toEqual(["Line 2: not an object"]);
    expect(parseJsonl("[1,").records).toEqual([]);
    expect(parseJsonl("[1,").errors).toHaveLength(1);
  });

  it("flattens list metadata", () => {
    expect(flattenValueList(null)).toEqual([]);
    expect(flattenValueList("a;b|c\nd")).toEqual(["a", "b", "c", "d"]);
    expect(flattenValueList('["x","y"]')).toEqual(["x", "y"]);
    expect(flattenValueList("a,b")).toEqual(["a,b"]);
    expect(flattenValueList({ a: 1, b: [2] })).toEqual(["1", "2"]);
    expect(flattenValueList("[bad")).toEqual(["[bad"]);
  });

  it("counts occurrences case-insensitively", () => {
    expect(countOccurrences("Aa aA", "aa")).toBe(2);
    expect(countOccurrences("abc", "")).toBe(0);
  });

  it("matches filter rows", () => {
    expect(valueMatches([], "empty", "")).toBe(true);
    expect(valueMatches("Hello", "has", "ell")).toBe(true);
    expect(valueMatches(["a", "B"], "eq", "b")).toBe(true);
    expect(valueMatches(5, "gte", 3)).toBe(true);
    expect(valueMatches("x", "unknown", "y")).toBe(true);
  });

  it("matches subset rules", () => {
    expect(subsetValueText(["a", { b: 1 }])).toBe('a {"b":1}');
    expect(
      subsetRuleMatches(
        { f: ["Alpha", "Beta"] },
        { field: "f", operator: "equals", value: "beta" },
      ),
    ).toBe(true);
    expect(
      subsetRuleMatches({ f: "Alpha" }, { field: "f", operator: "contains", value: "LPH" }, true),
    ).toBe(false);
    expect(subsetRuleMatches({ f: "x" }, { field: "f", operator: "regex", value: "[" })).toBe(
      false,
    );
    expect(subsetRuleMatches(null, { field: "f", operator: "missing" })).toBe(true);
    expect(subsetRuleMatches({ f: 1 }, { field: "f", operator: "bogus" })).toBe(false);
  });
});
