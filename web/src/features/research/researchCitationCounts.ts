/* Copyright © 2026 Aaron John Schlosser, PhD. AGPL-3.0-or-later. */
import type { ResearchResultEvidence } from "../../types/research";
import { parseResearchAnswer, segmentResearchAnswer } from "../../components/research/researchAnswerFormatting";

/** Count only run-local, unambiguously bound answer citations; not bibliography entries. */
export function evidenceCitationCounts(answer: string, evidence: ResearchResultEvidence[]): number[] {
  const counts = evidence.map(() => 0);
  for (const block of parseResearchAnswer(answer, "Works Cited")) {
    if (block.kind === "heading" && block.text?.trim().toLowerCase() === "works cited") break;
    for (const text of block.items ?? [block.text || ""]) {
      for (const segment of segmentResearchAnswer(text, evidence)) {
        if (segment.evidenceIndex !== undefined) counts[segment.evidenceIndex] += 1;
      }
    }
  }
  return counts;
}
