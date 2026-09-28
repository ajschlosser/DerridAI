/* Copyright 2026 Aaron John Schlosser, PhD. */
// Pure helpers for the review queue's lightweight row shape: deriving one from a full Record after
// an optimistic edit, previewing text the way the server does, and telling a queue row from a full
// Record so `selectRecord` can skip a redundant read when the caller already has one in hand.
import type { CorpusRecord } from "../../../api/corpus";
import type { CorpusQueueRow } from "../api/reviewReads";

/** Matches the server's truncation (`TEXT_PREVIEW_CHARS` in api/app/graphql/types/corpus.py). */
const TEXT_PREVIEW_CHARS = 240;

/** Whitespace-compacted preview, truncated with an ellipsis — never a mid-word cut left dangling. */
export function previewText(text: string): string {
  const compact = text.split(/\s+/).filter(Boolean).join(" ");
  if (compact.length <= TEXT_PREVIEW_CHARS) return compact;
  return `${compact.slice(0, TEXT_PREVIEW_CHARS - 1).trimEnd()}…`;
}

/** What `selectRecord` accepts: a lightweight queue row, or a full Record the caller already has. */
export type ReviewTargetLike = CorpusQueueRow | CorpusRecord;

/**
 * True when `target` is a full Record rather than a lightweight queue row. Queue rows carry
 * `text_preview`/`text_length` but never the full `text`; Records never carry `text_preview`. This
 * lets `selectRecord` skip a redundant read when the caller already has the full Record in hand
 * (for example a review-decision response's `next_record`).
 */
export function isFullRecord(target: ReviewTargetLike): target is CorpusRecord {
  return !("text_preview" in target);
}

/**
 * Re-derive a queue row from an updated Record. Used to patch `queueRows` in place after an
 * optimistic edit or an authoritative server response, without a round trip back through
 * `rows()`.
 */
export function queueRowFromRecord(record: CorpusRecord): CorpusQueueRow {
  const text = String(record.text || "");
  return {
    record_id: record.record_id,
    record_revision: record.record_revision ?? null,
    page_start: record.page_start == null ? null : String(record.page_start),
    page_end: record.page_end == null ? null : String(record.page_end),
    text_length: record.text_length ?? text.length,
    text_preview: previewText(text),
    review_state: record.review_state ?? null,
    review_disposition: record.review_disposition ?? null,
    review_issue_codes: record.review_issue_codes ?? [],
    metadata_llm_processed: Boolean(record.metadata_enrichment_finished),
    needs_review: Boolean(record.needs_review),
    source_quality_issues: Boolean(record.source_quality_issues?.length),
    metadata_complete: Boolean(record.metadata_complete),
  };
}

/** Whether a row's Record carries an unresolved source-quality problem worth its own warning icon. */
export function rowHasSourceWarning(row: CorpusQueueRow): boolean {
  return row.source_quality_issues;
}
