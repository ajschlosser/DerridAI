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

import type { ResearchThreadExport } from "../types/researchThreads";

type Translate = (key: string, values?: Record<string, string | number>) => string;

/**
 * Markdown view of a server-built export. Citations are the run's recorded strings and
 * identifiers are copied verbatim; nothing is reformatted or inferred here.
 */
export function researchThreadMarkdown(data: ResearchThreadExport, tf: Translate): string {
  const lines = [
    `# ${data.thread.title || data.thread.thread_id}`,
    "",
    `- ${tf("research.export_thread_id")}: \`${data.thread.thread_id}\``,
    `- ${tf("research.export_format")}: \`${data.format}\``,
    "",
  ];
  for (const turn of data.turns) {
    lines.push(`## ${turn.ordinal}. ${turn.question}`, "");
    const ids = [
      `${tf("research.export_turn_id")}: \`${turn.turn_id}\``,
      `${tf("research.export_attempt")}: ${turn.attempt}`,
    ];
    if (turn.research_run_id)
      ids.push(`${tf("research.export_run_id")}: \`${turn.research_run_id}\``);
    if (turn.model)
      ids.push(
        `${tf("research.export_model")}: ${[turn.provider, turn.model].filter(Boolean).join(" / ")}`,
      );
    lines.push(ids.join(" · "), "");
    if (turn.instructions)
      lines.push(`> ${tf("research.export_instructions")}: ${turn.instructions}`, "");
    lines.push(
      turn.answer_available && turn.answer
        ? turn.answer.trim()
        : `_${tf("research.export_no_answer", { status: turn.status })}_`,
      "",
    );
    if (turn.references.length) {
      lines.push(`### ${tf("research.export_references")}`, "");
      for (const ref of turn.references) {
        const revision = ref.record_revision == null ? "" : ` r${ref.record_revision}`;
        lines.push(
          `- ${ref.evidence_id ?? "?"}: ${ref.full_citation || ref.inline_citation || ""} — \`${ref.collection}/${ref.record_id}\`${revision}`,
        );
      }
      lines.push("");
    }
  }
  if (data.works_cited.length) {
    lines.push(`## ${tf("research.export_works_cited")}`, "");
    data.works_cited.forEach((citation, index) => lines.push(`${index + 1}. ${citation}`));
    lines.push("");
  }
  return lines.join("\n");
}

export function researchThreadExportName(data: ResearchThreadExport, extension: "md" | "json") {
  return `research-thread-${data.thread.thread_id}.${extension}`;
}
