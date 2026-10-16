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
import { evidenceCitationCounts } from "../../src/features/research/researchCitationCounts";
import {
  parseResearchAnswer,
  segmentResearchAnswer,
} from "../../src/components/research/researchAnswerFormatting";

describe("research answer formatting", () => {
  it("counts uniquely bound citations in prose and lists, but not Works Cited", () => {
    const evidence = [
      { evidence_id: "E1", inline_citation: "(Derrida 1997: 11)" },
      { evidence_id: "E2", inline_citation: "(Derrida 1997: 11)" },
      { evidence_id: "E3", inline_citation: "(Derrida 2002: 13)" },
    ];
    const answer =
      "An attribution [[E1]] and again [E1]. Ambiguous (Derrida 1997: 11)." +
      "\n\n- A further claim [[E3]].\n\nWorks Cited\n(Derrida 1997: 11) (Derrida 2002: 13)";
    expect(evidenceCitationCounts(answer, evidence)).toEqual([2, 0, 1]);
  });

  it("does not count unsupported or bibliography-only references", () => {
    const evidence = [{ evidence_id: "E1", inline_citation: "(Derrida 1997: 11)" }];
    expect(
      evidenceCitationCounts("Unknown [E9].\n\nWorks Cited\n(Derrida 1997: 11)", evidence),
    ).toEqual([0]);
  });

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

  it("renders single-delimiter emphasis such as foreign terms as italic, not literal asterisks", () => {
    expect(
      segmentResearchAnswer("Being as substance (*ousia*) or the _now_ of **presence**.", []),
    ).toEqual([
      { text: "Being as substance (" },
      { text: "ousia", italic: true },
      { text: ") or the " },
      { text: "now", italic: true },
      { text: " of " },
      { text: "presence", bold: true },
      { text: "." },
    ]);
  });

  it("keeps arithmetic, footnote asterisks and identifiers literal", () => {
    expect(segmentResearchAnswer("2 * 3 * 4, a note* and snake_case_name", [])).toEqual([
      { text: "2 * 3 * 4, a note* and snake_case_name" },
    ]);
  });

  it("keeps a citation bound when italic text precedes it", () => {
    const evidence = [{ evidence_id: "E0", inline_citation: "Derrida 1967: 23" }];
    expect(segmentResearchAnswer("The *stigmè* [E0].", evidence)).toEqual([
      { text: "The " },
      { text: "stigmè", italic: true },
      { text: " " },
      { text: "Derrida 1967: 23", evidenceIndex: 0 },
      { text: "." },
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

  it("resolves single and double evidence markers to the run's citation label", () => {
    const evidence = [{ evidence_id: "E7", inline_citation: "(Derrida 1997: 11)" }];

    for (const marker of ["[E7]", "[[E7]]"]) {
      expect(segmentResearchAnswer(`The claim remains provisional ${marker}.`, evidence)).toEqual([
        { text: "The claim remains provisional " },
        { text: "(Derrida 1997: 11)", evidenceIndex: 0 },
        { text: "." },
      ]);
    }
  });

  it("leaves unknown markers unlinked rather than attaching a nearby citation", () => {
    const evidence = [{ evidence_id: "E7", inline_citation: "(Derrida 1997: 11)" }];
    expect(segmentResearchAnswer("Unverified [E9].", evidence)).toEqual([
      { text: "Unverified [E9]." },
    ]);
  });

  it("does not silently bind an ambiguous human-readable citation to either record", () => {
    const evidence = [
      { evidence_id: "E1", inline_citation: "(Derrida 1997: 11)" },
      { evidence_id: "E2", inline_citation: "(Derrida 1997: 11)" },
    ];
    expect(segmentResearchAnswer("Ambiguous (Derrida 1997: 11).", evidence)).toEqual([
      { text: "Ambiguous (Derrida 1997: 11)." },
    ]);
    expect(segmentResearchAnswer("Specific [[E2]].", evidence)).toEqual([
      { text: "Specific " },
      { text: "(Derrida 1997: 11)", evidenceIndex: 1 },
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
