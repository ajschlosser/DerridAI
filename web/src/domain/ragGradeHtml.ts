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
import { tr } from "./sharedTranslate";

// Research grade card markup, shared by the job dialogs and the operations panel.
export function ragGradeHtml(grade: Record<string, unknown> = {}): string {
  const normalized = normalizeRagGrade(grade);
  const scoreKeys = [
    ["query_relevance", tr("faq.grade_query_relevance")],
    ["source_binding", tr("faq.grade_source_binding")],
    ["claim_traceability", tr("faq.grade_claim_traceability")],
    ["attribution_source_discrimination", tr("faq.grade_attribution_source_discrimination")],
    ["claim_evidence_fidelity", tr("faq.grade_claim_evidence_fidelity")],
    ["conceptual_precision", tr("faq.grade_conceptual_precision")],
    ["coverage", tr("faq.grade_coverage")],
    ["interpretive_usefulness", tr("faq.grade_interpretive_usefulness")],
    ["overall", tr("faq.grade_overall")],
  ];
  const sections: [string, string[]][] = [
    [tr("faq.grade_strengths"), [normalized.strengths].flat()],
    [tr("faq.grade_weaknesses"), [normalized.weaknesses].flat()],
    [tr("faq.grade_risky_claims"), [normalized.unsupported_or_risky_claims].flat()],
  ];
  return `<div class="rag-grade-content"><div class="rag-grade-scores">${scoreKeys.map(([key, name]) => `<div><span>${esc(name)}</span><strong>${esc(normalized.score(key))}</strong><small>/10</small></div>`).join("")}</div><section><b>${esc(tr("runtime.summary"))}</b><p>${esc(normalized.summary || tr("runtime.no_summary_returned"))}</p></section>${sections.map(([name, items]) => `<section><b>${esc(name)}</b><ul>${items.map((item) => `<li>${esc(item)}</li>`).join("") || `<li>${esc(tr("runtime.none_reported"))}</li>`}</ul></section>`).join("")}</div>`;
}
