/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  MIN_COLUMN_PERCENT,
  normalizeColumnWidths,
  scaleColumnWidth,
  setColumnWidth,
} from "../../src/domain/tableColumnWidths";

const sum = (widths: Record<string, number>) =>
  Math.round(Object.values(widths).reduce((a, b) => a + b, 0) * 10) / 10;

describe("table column widths", () => {
  it("starts from default shares that favour the text column and total 100", () => {
    const widths = normalizeColumnWidths(["record_id", "work", "text"]);
    expect(sum(widths)).toBe(100);
    expect(widths.text).toBeGreaterThan(widths.work);
    expect(widths.work).toBeGreaterThan(widths.record_id);
  });

  it("narrows the other columns proportionally when one is widened", () => {
    const keys = ["a", "b", "c"];
    const start = { a: 20, b: 30, c: 50 };
    const next = setColumnWidth(keys, start, "a", 60);
    expect(next.a).toBe(60);
    // b and c keep their 30:50 ratio in the remaining 40%.
    expect(next.b).toBe(15);
    expect(next.c).toBe(25);
    expect(sum(next)).toBe(100);
  });

  it("widens the others proportionally when one is narrowed", () => {
    const next = setColumnWidth(["a", "b", "c"], { a: 50, b: 25, c: 25 }, "a", 20);
    expect(next).toEqual({ a: 20, b: 40, c: 40 });
  });

  it("never lets any column fall below the minimum", () => {
    const keys = ["a", "b", "c", "d"];
    const next = setColumnWidth(keys, { a: 25, b: 25, c: 40, d: 10 }, "a", 99);
    expect(next.a).toBe(100 - MIN_COLUMN_PERCENT * 3);
    for (const key of ["b", "c", "d"]) expect(next[key]).toBeGreaterThanOrEqual(MIN_COLUMN_PERCENT);
    expect(sum(next)).toBe(100);
  });

  it("keeps saved proportions and gives a newly shown column its default share", () => {
    const widths = normalizeColumnWidths(["a", "b", "c"], { a: 60, b: 40 });
    expect(sum(widths)).toBe(100);
    expect(widths.a / widths.b).toBeCloseTo(1.5, 1);
    expect(widths.c).toBeGreaterThan(20);
  });

  it("drops widths of hidden columns and rescales the rest", () => {
    expect(normalizeColumnWidths(["a", "b"], { a: 30, b: 30, c: 40 })).toEqual({ a: 50, b: 50 });
  });

  it("scales one column and lets the others absorb the difference", () => {
    const next = scaleColumnWidth(["work", "text"], { work: 40, text: 60 }, "text", 0.75);
    expect(next).toEqual({ work: 55, text: 45 });
  });
});
