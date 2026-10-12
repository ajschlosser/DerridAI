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
import type { ResearchResult, ResearchResultEvidence } from "../../types/research";

export type ComparedPassage = {
  /** Record identity only; revision is compared, never merged. */
  recordId: string;
  collection: string;
  left: ResearchResultEvidence | null;
  right: ResearchResultEvidence | null;
  leftRevision: number | null;
  rightRevision: number | null;
  /** Both runs cite the record but at different (or unknown) revisions. */
  revisionDiffers: boolean;
};

export type ClaimStatusCounts = Record<string, number>;

function recordId(item: ResearchResultEvidence) {
  return String(item.record?.record_id ?? "").trim();
}
function revision(item: ResearchResultEvidence | null) {
  const value = Number(item?.record?.record_revision);
  return item && Number.isInteger(value) ? value : null;
}

/**
 * Aligns two runs' EvidenceRefs by collection and Record ID. Evidence without
 * a Record ID cannot be matched and is listed once per run. Each side keeps
 * its own run-scoped EvidenceRef, citation and revision.
 */
export function compareTurnEvidence(
  left: ResearchResult | null | undefined,
  right: ResearchResult | null | undefined,
): ComparedPassage[] {
  const rows = new Map<string, ComparedPassage>();
  const unmatched: ComparedPassage[] = [];
  const add = (item: ResearchResultEvidence, side: "left" | "right") => {
    const id = recordId(item);
    const collection = String(item.collection ?? "");
    const blank: ComparedPassage = {
      recordId: id,
      collection,
      left: null,
      right: null,
      leftRevision: null,
      rightRevision: null,
      revisionDiffers: false,
    };
    if (!id) {
      unmatched.push({ ...blank, [side]: item, [`${side}Revision`]: revision(item) });
      return;
    }
    const key = `${collection}\u0000${id}`;
    const row = rows.get(key) ?? blank;
    // Keep the first EvidenceRef per side; repeated markers name the same Record.
    if (!row[side]) {
      row[side] = item;
      row[`${side}Revision`] = revision(item);
    }
    rows.set(key, row);
  };
  (left?.evidence ?? []).forEach((item) => add(item, "left"));
  (right?.evidence ?? []).forEach((item) => add(item, "right"));
  for (const row of rows.values())
    row.revisionDiffers = Boolean(
      row.left &&
        row.right &&
        (row.leftRevision === null ||
          row.rightRevision === null ||
          row.leftRevision !== row.rightRevision),
    );
  return [...rows.values(), ...unmatched];
}

/** Claim validation counts per run; statuses are reported as recorded, not inferred. */
export function claimStatusCounts(result: ResearchResult | null | undefined): ClaimStatusCounts {
  const counts: ClaimStatusCounts = {};
  for (const claim of result?.claim_provenance?.claims ?? []) {
    const status = claim.validation_status || "unvalidated";
    counts[status] = (counts[status] || 0) + 1;
  }
  return counts;
}
