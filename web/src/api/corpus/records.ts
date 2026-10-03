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

import { apiRequest } from "../http";
import type { CorpusBuild, CorpusRecord, RecordContext, StructuralEditResult } from "./types";
import { LEGACY_CORPUS_BASE } from "./compatibility";

export const corpusRecordsApi = {
  records: (buildId: string, offset = 0, limit = 50, reviewQueue = "", query = "") =>
    apiRequest<{
      items: CorpusRecord[];
      total: number;
      offset: number;
      limit: number;
      queue_counts?: CorpusBuild["review_queue_counts"];
      metadata_values?: Record<string, string[]>;
    }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records?offset=${offset}&limit=${limit}${reviewQueue && reviewQueue !== "all" ? `&review_queue=${encodeURIComponent(reviewQueue)}` : ""}${query ? `&query=${encodeURIComponent(query)}` : ""}`,
    ),
  markViewed: (buildId: string, recordId: string) =>
    apiRequest<{ record_id: string; activity: CorpusRecord["activity"] }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/viewed`,
      { method: "POST" },
    ),
  patchText: (
    buildId: string,
    recordId: string,
    text: string,
    expectedRevision?: number,
    resolveSourceIssues = false,
  ) =>
    apiRequest<CorpusRecord>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/text`,
      {
        method: "PATCH",
        body: JSON.stringify({
          text,
          expected_revision: expectedRevision,
          resolve_source_issues: resolveSourceIssues,
        }),
      },
    ),
  /** Text of the records around one record, in document order (read-only context). */
  recordContext: (buildId: string, recordId: string, before = 3, after = 3) =>
    apiRequest<RecordContext>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/context?before=${before}&after=${after}`,
    ),
  merge: (
    buildId: string,
    recordId: string,
    direction: "previous" | "next",
    expectedRevision?: number,
  ) =>
    apiRequest<StructuralEditResult>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/merge`,
      { method: "POST", body: JSON.stringify({ direction, expected_revision: expectedRevision }) },
    ),
  /** Split after a source block (string) or at a character offset (number). */
  split: (buildId: string, recordId: string, at: string | number, expectedRevision?: number) =>
    apiRequest<StructuralEditResult>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/split`,
      {
        method: "POST",
        body: JSON.stringify({
          ...(typeof at === "string" ? { after_block_id: at } : { offset: at }),
          expected_revision: expectedRevision,
        }),
      },
    ),
  createFromSelection: (
    buildId: string,
    recordId: string,
    selection: {
      start: number;
      end: number;
      left: "distinct" | "merge_prior";
      right: "distinct" | "merge_next";
      expectedRevision?: number;
    },
  ) =>
    apiRequest<StructuralEditResult>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/from-selection`,
      {
        method: "POST",
        body: JSON.stringify({
          start: selection.start,
          end: selection.end,
          left: selection.left,
          right: selection.right,
          expected_revision: selection.expectedRevision,
        }),
      },
    ),
  previewRecord: (buildId: string, recordId: string) =>
    apiRequest<{
      record: Record<string, unknown>;
      jsonl: string;
      validation_errors: string[];
      unresolved_fields: string[];
      would_publish: boolean;
    }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/preview`,
    ),
  touchupText: (buildId: string, recordId: string, payload: Record<string, unknown>) =>
    apiRequest<{
      record_id: string;
      source_text: string;
      proposed_text: string;
      changes: string[];
      warnings: string[];
      provider: string;
      model: string;
      proposal_id?: string;
      run_id?: string;
      created_at?: string;
      no_change?: boolean;
    }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/text-touchup`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  setTouchupProposalStatus: (
    buildId: string,
    recordId: string,
    status: "pending_review" | "dismissed",
  ) =>
    apiRequest<CorpusRecord>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/text-touchup-proposal`,
      { method: "PATCH", body: JSON.stringify({ status }) },
    ),
};
