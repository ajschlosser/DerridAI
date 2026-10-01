import { describe, expect, it } from "vitest";
import {
  parseResearchAnswer,
  segmentResearchAnswer,
} from "../../src/components/research/researchAnswerFormatting";

describe("research answer formatting", () => {
  it("does not turn a generated paragraph wrapped in strong markers into a bold paragraph", () => {
    const blocks = parseResearchAnswer(
      "**Responsibility cannot be reduced to a programmable rule because the decision remains exposed to undecidability.**",
      "Works Cited",
    );

    expect(blocks).toEqual([
      {
        kind: "paragraph",
        text: "Responsibility cannot be reduced to a programmable rule because the decision remains exposed to undecidability.",
      },
    ]);
    expect(segmentResearchAnswer(blocks[0].text || "", [])).toEqual([
      {
        text: "Responsibility cannot be reduced to a programmable rule because the decision remains exposed to undecidability.",
      },
    ]);
  });

  it("keeps deliberate inline emphasis local to the emphasized words", () => {
    expect(segmentResearchAnswer("The decision is **not programmable** in advance.", [])).toEqual([
      { text: "The decision is " },
      { text: "not programmable", bold: true },
      { text: " in advance." },
    ]);
  });

  it("binds a citation even when the model wrapped all or part of it in bold markers", () => {
    const evidence = [
      {
        evidence_id: "E1",
        inline_citation: "(Author 1999: 20–21)",
      },
    ];

    expect(
      segmentResearchAnswer(
        "A decision exceeds calculation **(Author **1999**: 20–21)**.",
        evidence,
      ),
    ).toEqual([
      { text: "A decision exceeds calculation " },
      { text: "(Author 1999: 20–21)", evidenceIndex: 0 },
      { text: "." },
    ]);
  });

  it("keeps unresolved evidence markers inspectable instead of losing their binding", () => {
    const evidence = [{ evidence_id: "E7", inline_citation: "(Author 1997: 11)" }];

    expect(segmentResearchAnswer("The claim remains provisional [E7].", evidence)).toEqual([
      { text: "The claim remains provisional " },
      { text: "[E7]", evidenceIndex: 0 },
      { text: "." },
    ]);
  });

  it("drops unmatched strong delimiters rather than leaking bold state through the rest of a block", () => {
    expect(
      segmentResearchAnswer("A stable opening **followed by an unfinished emphasis", []),
    ).toEqual([{ text: "A stable opening followed by an unfinished emphasis" }]);
  });

  it("normalizes hard-wrapped prose into a single paragraph and preserves list structure", () => {
    const blocks = parseResearchAnswer(
      "This sentence was hard wrapped by a model\nbut is still one paragraph.\n\n1. First point\n2. Second point",
      "Works Cited",
    );

    expect(blocks).toEqual([
      {
        kind: "paragraph",
        text: "This sentence was hard wrapped by a model but is still one paragraph.",
      },
      {
        kind: "ordered",
        items: ["First point", "Second point"],
      },
    ]);
  });
});
