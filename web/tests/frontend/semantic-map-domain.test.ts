// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import { radialLayout, segmentText } from "../../src/features/corpus-builder/domain/semanticMap";

const text = "Author reads Levinas on hospitality.";
const span = (surface: string, layer: string) => {
  const start = text.indexOf(surface);
  return { start, end: start + surface.length, layer };
};

describe("segmentText", () => {
  it("conserves the text and marks only shown layers", () => {
    const spans = [span("Author", "ner"), span("Levinas", "entity"), span("hospitality", "pos")];
    const segments = segmentText(text, spans, new Set(["ner", "pos"]));
    expect(segments.map((segment) => segment.text).join("")).toBe(text);
    expect(segments.filter((segment) => segment.mention).map((segment) => segment.text)).toEqual([
      "Author",
      "hospitality",
    ]);
  });

  it("keeps the earliest, then longest, span when spans overlap", () => {
    const spans = [
      span("Levinas", "ner"),
      span("Levinas on hospitality", "quotation"),
      span("on", "pos"),
    ];
    const segments = segmentText(text, spans, new Set(["ner", "quotation", "pos"]));
    expect(segments.map((segment) => segment.text).join("")).toBe(text);
    expect(segments.filter((segment) => segment.mention).map((segment) => segment.text)).toEqual([
      "Levinas on hospitality",
    ]);
  });

  it("ignores spans that fall outside the text", () => {
    const segments = segmentText(text, [{ start: 30, end: 90, layer: "ner" }], new Set(["ner"]));
    expect(segments).toEqual([{ text, start: 0, mention: null }]);
  });
});

describe("radialLayout", () => {
  const size = { width: 400, height: 400 };

  it("centres the focus and places rings deterministically", () => {
    const first = radialLayout("c", ["a", "b"], ["x"], size);
    expect(first.get("c")).toEqual({ x: 200, y: 200 });
    expect(first.get("a")).toEqual({ x: 200, y: 100 });
    expect(radialLayout("c", ["a", "b"], ["x"], size)).toEqual(first);
  });

  it("draws an outer node beside the inner node it is attached to", () => {
    const positions = radialLayout(
      "c",
      ["top", "right", "bottom", "left"],
      ["o1", "o2", "o3", "o4"],
      size,
      new Map([["o1", "bottom"]]),
    );
    const bottom = positions.get("bottom")!;
    const o1 = positions.get("o1")!;
    expect(Math.abs(o1.x - bottom.x)).toBeLessThan(1);
    expect(o1.y).toBeGreaterThan(bottom.y);
    expect(new Set([...positions.values()].map((point) => `${point.x},${point.y}`)).size).toBe(9);
  });
});
