/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
        inline_citation: "(Derrida 1999: 20–21)",
      },
    ];

    expect(
      segmentResearchAnswer(
        "A decision exceeds calculation **(Derrida **1999**: 20–21)**.",
        evidence,
      ),
    ).toEqual([
      { text: "A decision exceeds calculation " },
      { text: "(Derrida 1999: 20–21)", evidenceIndex: 0 },
      { text: "." },
    ]);
  });

  it("keeps unresolved evidence markers inspectable instead of losing their binding", () => {
    const evidence = [{ evidence_id: "E7", inline_citation: "(Derrida 1997: 11)" }];

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
