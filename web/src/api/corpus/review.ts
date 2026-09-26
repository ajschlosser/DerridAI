/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "../http";
import type { CorpusBuild, CorpusRecord } from "./types";
import { LEGACY_CORPUS_BASE } from "./compatibility";

export const corpusReviewApi = {
  accept: (buildId: string, recordId: string, accepted = true, expectedRevision?: number) =>
    apiRequest<CorpusRecord>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/accept`,
      { method: "POST", body: JSON.stringify({ accepted, expected_revision: expectedRevision }) },
    ),
  disposition: (
    buildId: string,
    recordId: string,
    disposition: "pending" | "accepted" | "rejected",
    reason = "",
    expectedRevision?: number,
  ) =>
    apiRequest<CorpusRecord>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/disposition`,
      {
        method: "POST",
        body: JSON.stringify({ disposition, reason, expected_revision: expectedRevision }),
      },
    ),
  reviewDecision: (
    buildId: string,
    recordId: string,
    disposition: "accepted" | "rejected",
    reason = "",
    expectedRevision?: number,
    reviewQueue?: string,
  ) =>
    apiRequest<{
      applied: boolean;
      blocked: boolean;
      blocker?: string;
      blocking_fields?: string[];
      record: CorpusRecord;
      next_record?: CorpusRecord | null;
      build: CorpusBuild;
      queue_counts?: CorpusBuild["review_queue_counts"];
    }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/review-decision`,
      {
        method: "POST",
        body: JSON.stringify({
          disposition,
          reason,
          expected_revision: expectedRevision,
          review_queue: reviewQueue || null,
        }),
      },
    ),
  bulkDisposition: (
    buildId: string,
    disposition: "pending" | "accepted" | "rejected",
    reviewQueue: string | null,
    query = "",
    reason = "",
    recordIds: string[] = [],
  ) =>
    apiRequest<{
      changed: number;
      disposition: string;
      blocked_metadata?: number;
      blocked_record_ids?: string[];
      queue_counts?: CorpusBuild["review_queue_counts"];
    }>(`${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/disposition`, {
      method: "POST",
      body: JSON.stringify({
        disposition,
        reason,
        review_queue:
          reviewQueue && !["all", "accepted", "rejected"].includes(reviewQueue)
            ? reviewQueue
            : null,
        filter_disposition:
          reviewQueue === "accepted" ? "accepted" : reviewQueue === "rejected" ? "rejected" : null,
        query,
        record_ids: recordIds,
      }),
    }),
  undoReview: (buildId: string) =>
    apiRequest<{
      restored: boolean;
      action?: string;
      selected_record_id?: string;
      record_count: number;
      can_undo?: boolean;
      can_redo?: boolean;
    }>(`${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/review/undo`, {
      method: "POST",
    }),
  redoReview: (buildId: string) =>
    apiRequest<{
      restored: boolean;
      action?: string;
      selected_record_id?: string;
      record_count: number;
      can_undo?: boolean;
      can_redo?: boolean;
    }>(`${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/review/redo`, {
      method: "POST",
    }),
  adjudicateBoundary: (
    buildId: string,
    recordId: string,
    direction: "previous" | "next",
    payload: Record<string, unknown> = {},
  ) =>
    apiRequest<{
      decision: Record<string, unknown>;
      left_record: CorpusRecord;
      right_record: CorpusRecord;
      build: CorpusBuild;
    }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/boundary-adjudication`,
      { method: "POST", body: JSON.stringify({ direction, ...payload }) },
    ),
};
