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

import { esc } from "./html";
import { normalizeRagGrade } from "./sharedRecordHelpers";

// Research grade card markup, shared by the job dialogs and the operations panel.
export function ragGradeHtml(grade: Record<string, unknown> = {}): string {
  const normalized = normalizeRagGrade(grade);
  const scoreKeys = [
    ["query_relevance", "Query relevance"],
    ["source_binding", "Source binding"],
    ["claim_traceability", "Claim traceability"],
    ["attribution_source_discrimination", "Attribution/source discrimination"],
    ["claim_evidence_fidelity", "Claim/evidence fidelity"],
    ["conceptual_precision", "Conceptual precision"],
    ["coverage", "Coverage"],
    ["interpretive_usefulness", "Interpretive usefulness"],
    ["overall", "Overall"],
  ];
  const sections: [string, string[]][] = [
    ["Strengths", [normalized.strengths].flat()],
    ["Weaknesses", [normalized.weaknesses].flat()],
    ["Unsupported or risky claims", [normalized.unsupported_or_risky_claims].flat()],
  ];
  return `<div class="rag-grade-content"><div class="rag-grade-scores">${scoreKeys.map(([key, name]) => `<div><span>${esc(name)}</span><strong>${esc(normalized.score(key))}</strong><small>/10</small></div>`).join("")}</div><section><b>Summary</b><p>${esc(normalized.summary || "No summary returned.")}</p></section>${sections.map(([name, items]) => `<section><b>${esc(name)}</b><ul>${items.map((item) => `<li>${esc(item)}</li>`).join("") || "<li>None reported.</li>"}</ul></section>`).join("")}</div>`;
}
