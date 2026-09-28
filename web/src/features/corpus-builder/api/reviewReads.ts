/* Copyright 2026 Aaron John Schlosser, PhD. */
// Corpus Builder review reads: the read-only GraphQL façade behind the review queue
// (docs/GRAPHQL.md). A queue page returns lightweight rows; a full reviewer-presented Record is
// read one at a time, when a row is opened. Commands (accept/reject/edit/merge/...) stay on REST
// (../../../api/corpus): this module only reads.
import { execute, type ExecuteOptions } from "../../../api/graphql/client";
import {
  CorpusMetadataFacetsDocument,
  CorpusQueueRowsDocument,
  CorpusQueueTextsDocument,
  CorpusReviewQueueDocument,
  CorpusReviewRecordsDocument,
  type CorpusQueueRowFieldsFragment,
} from "../../../api/graphql/generated";
import type { CorpusRecord } from "../../../api/corpus";
import type { ReviewQueue } from "../../../types/corpus";

/**
 * One review-queue row: identifiers, page labels, review state and a short preview. Never the
 * full text or metadata (that is `CorpusRecord`, read one at a time when a row is opened).
 */
export type CorpusQueueRow = CorpusQueueRowFieldsFragment;

export interface CorpusQueueCounts {
  all: number;
  ready: number;
  preparing: number;
  issues: number;
  metadata: number;
  topology: number;
  source: number;
  accepted: number;
  rejected: number;
  pending: number;
}

export interface CorpusQueuePage {
  rows: CorpusQueueRow[];
  total: number;
  offset: number;
  limit: number;
  hasNextPage: boolean;
  /**
   * The whole build's row count (`queue_counts.all`), independent of the active filter/search —
   * used to track when the build's full topology has been hydrated at least once.
   */
  topologyCount: number;
  counts: CorpusQueueCounts;
}

export interface CorpusQueueFilters {
  needsReview?: boolean;
  disposition?: string;
  metadataIncomplete?: boolean;
  sourceProblem?: boolean;
  reviewQueue?: ReviewQueue | "";
  query?: string;
}

function queueArguments(filters: CorpusQueueFilters) {
  const queue = filters.reviewQueue && filters.reviewQueue !== "all" ? filters.reviewQueue : null;
  return {
    needs_review: filters.needsReview ?? null,
    disposition: filters.disposition ?? null,
    metadata_incomplete: filters.metadataIncomplete ?? null,
    source_problem: filters.sourceProblem ?? null,
    review_queue: queue,
    query: filters.query ?? "",
  };
}

function definedRows(rows: ReadonlyArray<CorpusQueueRow | null | undefined>): CorpusQueueRow[] {
  return rows.filter((row): row is CorpusQueueRow => row != null);
}

export const corpusReviewReads = {
  /** The paged, filtered review queue (REST: GET /api/pdf/corpus-builds/{id}/records). */
  async queuePage(
    buildId: string,
    offset: number,
    limit: number,
    filters: CorpusQueueFilters = {},
    options: ExecuteOptions = {},
  ): Promise<CorpusQueuePage> {
    const { corpus_build } = await execute(
      CorpusReviewQueueDocument,
      { build_id: buildId, offset, limit, ...queueArguments(filters) },
      options,
    );
    const page = corpus_build.review_queue;
    return {
      rows: page.items,
      total: page.total,
      offset: page.offset,
      limit: page.limit,
      hasNextPage: page.offset + page.items.length < page.total,
      topologyCount: page.queue_counts.all,
      counts: page.queue_counts,
    };
  },

  /** Queue-row projections for specific Records, in the order requested (used to patch rows in place). */
  async rows(
    buildId: string,
    recordIds: readonly string[],
    options: ExecuteOptions = {},
  ): Promise<CorpusQueueRow[]> {
    if (!recordIds.length) return [];
    const { corpus_build } = await execute(
      CorpusQueueRowsDocument,
      { build_id: buildId, record_ids: [...recordIds] },
      options,
    );
    return definedRows(corpus_build.rows);
  },

  /** Full reviewer-presented Records, read one at a time when a queue row is opened. */
  async records(
    buildId: string,
    recordIds: readonly string[],
    options: ExecuteOptions = {},
  ): Promise<CorpusRecord[]> {
    if (!recordIds.length) return [];
    const { corpus_build } = await execute(
      CorpusReviewRecordsDocument,
      { build_id: buildId, record_ids: [...recordIds] },
      options,
    );
    return corpus_build.records
      .filter((record): record is NonNullable<typeof record> => record != null)
      .map((record) => record.review_document as CorpusRecord);
  },

  /** Just the text of the given records, for the clean-up dialog's repeated-running-head detection. */
  async texts(
    buildId: string,
    recordIds: readonly string[],
    options: ExecuteOptions = {},
  ): Promise<string[]> {
    if (!recordIds.length) return [];
    const { corpus_build } = await execute(
      CorpusQueueTextsDocument,
      { build_id: buildId, record_ids: [...recordIds] },
      options,
    );
    return corpus_build.records
      .filter((record): record is NonNullable<typeof record> => record != null)
      .map((record) => record.text);
  },

  /** Build-wide observed metadata values, optionally narrowed to specific fields. */
  async metadataFacets(
    buildId: string,
    fields: readonly string[] = [],
    options: ExecuteOptions = {},
  ): Promise<Record<string, string[]>> {
    const { corpus_build } = await execute(
      CorpusMetadataFacetsDocument,
      { build_id: buildId, fields: fields.length ? [...fields] : null },
      options,
    );
    return (corpus_build.metadata_facets as Record<string, string[]> | null) || {};
  },
};
