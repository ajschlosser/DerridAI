/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  highlight,
  highlightTerms,
  modelOptionLabel,
  openAiModelMatchesKind,
  semanticSimilarity,
  snippet,
} from "../../src/domain/recordFormatting";
import {
  compactRecordHistory,
  normalizePdfLinkChanges,
  pdfLinks,
  recordPayload,
} from "../../src/domain/recordPayloads";

// These behaviors were checked against the original legacy runtime.js functions across a wide input matrix.
describe("record formatting", () => {
  it("highlights a query and escapes the text", () => {
    expect(highlight("A <b>Hello</b>", "hello")).toBe("A &lt;b&gt;<mark>Hello</mark>&lt;/b&gt;");
    expect(highlight("x", "")).toBe("x");
    expect(highlightTerms("The Sign and the sign", "sign the")).toBe(
      "<mark>The</mark> <mark>Sign</mark> and <mark>the</mark> <mark>sign</mark>",
    );
    expect(highlightTerms("plain & simple", "")).toBe("plain &amp; simple");
  });
  it("cuts snippets around the match", () => {
    const text = "x".repeat(300) + " needle " + "y".repeat(300);
    const out = snippet(text, "needle", 40);
    expect(out.startsWith("…")).toBe(true);
    expect(out.endsWith("…")).toBe(true);
    expect(out).toContain("needle");
    expect(snippet("  a   b ", null)).toBe("a b");
    expect(snippet(null, "x")).toBe("");
  });
  it("turns distances into similarity", () => {
    expect(semanticSimilarity(0)).toBe(1);
    expect(semanticSimilarity(1)).toBe(0.5);
    expect(semanticSimilarity(-1)).toBe(1);
    expect(semanticSimilarity("x")).toBeNull();
  });
  it("labels models and matches model kinds", () => {
    expect(modelOptionLabel({ name: "m", parameter_size: "7B", quantization_level: "Q4" })).toBe(
      "m · 7B · Q4",
    );
    expect(modelOptionLabel({ name: "m" })).toBe("m");
    expect(openAiModelMatchesKind("deepseek-r1", "reasoning")).toBe(true);
    expect(openAiModelMatchesKind("gpt-4o", "coding")).toBe(false);
    expect(openAiModelMatchesKind("anything", "any")).toBe(true);
    expect(openAiModelMatchesKind("anything", "bogus")).toBe(false);
  });
});

describe("record payloads", () => {
  const record = {
    a: 1,
    updates: [{ field_name: "a", source: "llm" }],
    _updates_count: 1,
    _chroma_id: "c",
  };
  it("drops bookkeeping unless asked", () => {
    expect(recordPayload(record)).toEqual({ a: 1 });
    expect(recordPayload(record, { includeUpdates: true, includeChromaId: true })).toEqual({
      a: 1,
      updates: record.updates,
      _chroma_id: "c",
    });
    expect(recordPayload(record, { fields: ["a", "zzz", "a"] })).toEqual({ a: 1 });
    expect(recordPayload(null)).toEqual({});
  });
  it("summarizes history, newest first", () => {
    const history = compactRecordHistory({
      updates: [{ field_name: "a" }, { field_name: "b", source: "llm" }],
    });
    expect(history.map((h) => [h.id, h.field_name, h.source])).toEqual([
      ["history-1", "b", "llm"],
      ["history-0", "a", "manual"],
    ]);
    expect(compactRecordHistory(null)).toEqual([]);
  });
  it("reads PDF links from every stored shape", () => {
    expect(pdfLinks({ pdf_file: "f", pdf_pages: [3, "2", 2, 0, "x"] })).toEqual([
      { pdf_file: "f", pdf_page: 2 },
      { pdf_file: "f", pdf_page: 3 },
    ]);
    expect(pdfLinks({ pdf_file: "f", pdf_page: 4 })).toEqual([{ pdf_file: "f", pdf_page: 4 }]);
    expect(
      pdfLinks({
        pdf_links: [
          { pdf_file: "g", pdf_page: 9 },
          { pdf_file: "", pdf_page: 1 },
        ],
      }),
    ).toEqual([{ pdf_file: "g", pdf_page: 9 }]);
    expect(pdfLinks(null)).toEqual([]);
  });
  it("normalizes PDF link changes", () => {
    expect(
      normalizePdfLinkChanges({ pdf_page: 1 }, [
        { pdf_file: "f", pdf_page: 3 },
        { pdf_file: "f", pdf_page: "1" },
      ]),
    ).toEqual({ pdf_file: "f", pdf_pages: [1, 3], pdf_page: null });
    expect(() =>
      normalizePdfLinkChanges({}, [
        { pdf_file: "f", pdf_page: 1 },
        { pdf_file: "g", pdf_page: 1 },
      ]),
    ).toThrow("multiple PDF files");
  });
});
