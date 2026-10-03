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

import type {
  EvidenceSuggestion,
  MetadataPrecedents,
  PrecedentCandidateUnit,
} from "../api/corpus/metadata";

/**
 * This record's own blocks that resemble any precedent's reviewed evidence, best first, one entry per block.
 * Only blocks listed in `recordBlockIds` survive: a precedent's evidence belongs to another record and is
 * never offered as this record's citation.
 */
export function precedentEvidenceSuggestions(
  result: MetadataPrecedents | null | undefined,
  recordBlockIds: Iterable<string>,
): EvidenceSuggestion[] {
  const members = new Set(Array.from(recordBlockIds, String));
  const best = new Map<string, PrecedentCandidateUnit>();
  for (const item of result?.items || []) {
    for (const unit of item.candidate_source_units || []) {
      if (!members.has(unit.block_id)) continue;
      const prior = best.get(unit.block_id);
      if (!prior || unit.score > prior.score) best.set(unit.block_id, unit);
    }
  }
  return [...best.values()]
    .sort((a, b) => b.score - a.score || a.block_id.localeCompare(b.block_id))
    .map((unit) => ({
      block_id: unit.block_id,
      score: unit.score,
      method: unit.method,
      reason: "",
    }));
}

/** Where a candidate sits in its own medium: a page, a time range, or its position in the record. */
export function candidateLocation(
  unit: PrecedentCandidateUnit,
  recordBlockIds: string[],
):
  | { kind: "page"; page: string }
  | { kind: "time"; start: number; end: number }
  | { kind: "passage"; index: number } {
  const page = unit.printed_page_label || (unit.page !== undefined ? String(unit.page) : "");
  if (page) return { kind: "page", page };
  if (typeof unit.start === "number" && typeof unit.end === "number")
    return { kind: "time", start: unit.start, end: unit.end };
  return { kind: "passage", index: recordBlockIds.indexOf(unit.block_id) + 1 };
}
