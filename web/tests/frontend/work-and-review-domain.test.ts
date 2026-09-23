/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import * as touchup from "../../src/domain/touchupFields";
import * as review from "../../src/domain/reviewPresentation";
import * as work from "../../src/domain/workMetadata";

// The snapshots were verified to be identical to the original legacy runtime.js functions, over these
// inputs, before they were recorded.
const mk = (r: object) => ({ file: { name: "f" }, record: r, index: 0 });
const rowsets = [
  [],
  [mk({})],
  [
    mk({ work: "W", source: "s", document_author: "A", cover_url: "http://x/c.jpg", year: 1967 }),
    mk({ work: "W", document_author: "A", year: 1967 }),
    mk({ work: "W", document_author: "B", year: 1970, topics: ["a"] }),
  ],
  [mk({ work: "X", cover_url: "", topics: ["a"] }), mk({ work: "X", topics: ["a"] })],
];

describe("work metadata helpers", () => {
  it("summarizes a work's rows", () => {
    for (const rows of rowsets) {
      expect([
        work.representativeWorkMetadata(rows),
        work.workOverviewMetadataRows(rows),
        work.workCoverUrl(rows),
      ]).toMatchSnapshot();
    }
    expect(work.commonWorkValue(rowsets[2], "work")).toEqual({ mixed: false, value: "W" });
    expect(work.commonWorkValue(rowsets[2], "document_author")).toMatchObject({ mixed: true });
  });
});

describe("touch-up fields", () => {
  it("offers known groups first, then the record's own fields", () => {
    expect(
      touchup.touchupFieldsForRecord({
        text: "t",
        topics: ["a"],
        _x: 1,
        text_length: 4,
        custom: 1,
      }),
    ).toMatchSnapshot();
  });
});

describe("review presentation", () => {
  it("builds diff sides and pretty JSON", () => {
    expect(review.reviewDiffSides("a b c", "a x c")).toMatchSnapshot();
    expect(review.llmDiffSides("topics", ["a"], ["a", "b"])).toMatchSnapshot();
    expect(review.llmDiffSummary("Keep this wording.", "Keep this exact wording.")).toEqual({
      removed: 0,
      added: 1,
      before: 3,
      after: 4,
    });
    expect(review.jsonPretty({ a: 1 })).toMatchSnapshot();
  });
  it("renders a RAG answer as escaped paragraphs", () => {
    expect(review.ragAnswerHtml("")).toBe('<div class="llm-empty">No answer returned.</div>');
    expect(review.ragAnswerHtml("one\n\ntwo <i>")).toMatchSnapshot();
  });
  it("matches annotations against a query", () => {
    const item = {
      work: "W",
      record: { record_id: "r1" },
      file: { name: "f" },
      annotation: { note: "Hello", tags: ["t1"] },
    };
    expect(review.annotationMatches(item, "hello")).toBe(true);
    expect(review.annotationMatches(item, "zzz")).toBe(false);
    expect(review.annotationMatches(item, "")).toBe(true);
  });
});
