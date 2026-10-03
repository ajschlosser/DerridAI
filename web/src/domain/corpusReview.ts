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

import type { CorpusRecord } from "../api/pdfCorpus";

/** Prefer authoritative queue/state values, with legacy-record fallbacks. */
export function recordIssueKinds(record: CorpusRecord) {
  if (Array.isArray(record.review_issue_codes))
    return record.review_issue_codes.filter((code) =>
      ["source", "metadata", "topology"].includes(String(code)),
    );
  const issues: string[] = [];
  if (record.source_quality_issues?.length) issues.push("source");
  if (
    (record.metadata_incomplete_fields || []).length ||
    (record.metadata_review_fields || []).length
  )
    issues.push("metadata");
  const reason = String(record.review_reason || "").toLowerCase();
  if (
    record.needs_review &&
    ["boundary", "merge", "split", "topology"].some((token) => reason.includes(token))
  )
    issues.push("topology");
  return issues;
}
export function recordState(record: CorpusRecord) {
  const authoritative = String(record.review_state || "");
  if (
    ["preparing", "ready", "metadata", "topology", "source", "accepted", "rejected"].includes(
      authoritative,
    )
  )
    return authoritative;
  if (record.accepted) return "accepted";
  if (record.rejected) return "rejected";
  const issues = recordIssueKinds(record);
  return issues[0] || "ready";
}
