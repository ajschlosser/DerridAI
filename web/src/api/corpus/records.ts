/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "../http";
import type { CorpusBuild, CorpusRecord } from "./types";
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
  merge: (
    buildId: string,
    recordId: string,
    direction: "previous" | "next",
    expectedRevision?: number,
  ) =>
    apiRequest<CorpusRecord>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/merge`,
      { method: "POST", body: JSON.stringify({ direction, expected_revision: expectedRevision }) },
    ),
  split: (buildId: string, recordId: string, afterBlockId: string, expectedRevision?: number) =>
    apiRequest<{ records: CorpusRecord[] }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/split`,
      {
        method: "POST",
        body: JSON.stringify({ after_block_id: afterBlockId, expected_revision: expectedRevision }),
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
