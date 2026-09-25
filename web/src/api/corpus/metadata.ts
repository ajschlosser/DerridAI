/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "../http";
import type { CorpusBuild, CorpusRecord, EnrichmentMetrics } from "./types";
import { LEGACY_CORPUS_BASE, legacyCorpusUrl } from "./compatibility";

export const corpusMetadataApi = {
  metadataDecision: (
    buildId: string,
    recordId: string,
    field: string,
    value: unknown,
    expectedRevision?: number,
    confirmNoSupportedValue = false,
  ) =>
    apiRequest<{
      applied: boolean;
      record: CorpusRecord;
      build: CorpusBuild;
      queue_counts?: CorpusBuild["review_queue_counts"];
      remaining_fields?: string[];
      ready_for_acceptance?: boolean;
      review_state?: string;
    }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/metadata-decision`,
      {
        method: "POST",
        body: JSON.stringify({
          field,
          value,
          expected_revision: expectedRevision,
          confirm_no_supported_value: confirmNoSupportedValue,
        }),
      },
    ),
  metadataDecisionBatch: (
    buildId: string,
    recordId: string,
    changes: Record<string, unknown>,
    expectedRevision?: number,
  ) =>
    apiRequest<{
      applied: boolean;
      record: CorpusRecord;
      build: CorpusBuild;
      changed_fields: string[];
    }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/metadata-decisions`,
      {
        method: "POST",
        body: JSON.stringify({ changes, expected_revision: expectedRevision }),
      },
    ),
  metadataCache: (buildId: string, recordId: string, field: string) =>
    apiRequest<{ suggestions: Record<string, unknown> }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/metadata-cache?field=${encodeURIComponent(field)}`,
    ),
  clearMetadataCache: (buildId: string, recordId: string, field?: string) =>
    apiRequest<{ cleared: number }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/metadata-cache`,
      {
        method: "DELETE",
        body: JSON.stringify(field ? { field } : {}),
      },
    ),
  clearAllMetadataCache: () =>
    apiRequest<{ cleared: number }>(legacyCorpusUrl("metadata-cache"), { method: "DELETE" }),
  bulkMetadata: (
    buildId: string,
    changes: Record<string, unknown>,
    options: {
      recordIds?: string[];
      applyToAll?: boolean;
      reviewQueue?: string | null;
      query?: string;
    } = {},
  ) =>
    apiRequest<{
      changed: number;
      record_ids: string[];
      queue_counts?: CorpusBuild["review_queue_counts"];
    }>(`${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/metadata`, {
      method: "PATCH",
      body: JSON.stringify({
        changes,
        record_ids: options.recordIds || [],
        apply_to_all: Boolean(options.applyToAll),
        review_queue:
          options.reviewQueue && !["all"].includes(options.reviewQueue)
            ? options.reviewQueue
            : null,
        query: options.query || "",
      }),
    }),
  requeueMetadata: (buildId: string, recordId: string, payload: Record<string, unknown>) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/rerun-metadata`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  patchMetadata: (
    buildId: string,
    recordId: string,
    changes: Record<string, unknown>,
    expectedRevision?: number,
    includeState = false,
  ) =>
    apiRequest<
      | CorpusRecord
      | {
          record: CorpusRecord;
          build: CorpusBuild;
          queue_counts?: CorpusBuild["review_queue_counts"];
        }
    >(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/metadata${includeState ? "?include_state=true" : ""}`,
      { method: "PATCH", body: JSON.stringify({ changes, expected_revision: expectedRevision }) },
    ),
  patchEvidence: (
    buildId: string,
    recordId: string,
    field: string,
    blockIds: string[],
    confidence = 1,
    reason = "",
    expectedRevision?: number,
  ) =>
    apiRequest<CorpusRecord>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/evidence`,
      {
        method: "PATCH",
        body: JSON.stringify({
          field,
          block_ids: blockIds,
          confidence,
          reason,
          expected_revision: expectedRevision,
        }),
      },
    ),
  retryMetadata: (buildId: string, payload: Record<string, unknown>) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/metadata/retry`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  rerunMetadata: (buildId: string, recordId: string, payload: Record<string, unknown>) =>
    apiRequest<CorpusRecord>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/rerun-metadata`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  enrichmentMetrics: (buildId: string) =>
    apiRequest<EnrichmentMetrics>(
      `${LEGACY_CORPUS_BASE}/corpus-enrichment-metrics?build_id=${encodeURIComponent(buildId)}`,
    ),
  rerunMetadataEnrichment: (buildId: string, payload: Record<string, unknown>) =>
    apiRequest<CorpusBuild>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/metadata/enrich`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  editorialMemory: (buildId: string) =>
    apiRequest<{
      conventions: Record<string, { value: unknown; confirmed_records: number }>;
      examples: Record<
        string,
        Array<{ record_id: string; value: unknown; similarity: number; excerpt: string }>
      >;
      reset_at?: string | null;
      convention_count: number;
      example_count: number;
    }>(`${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/editorial-memory`),
  resetEditorialMemory: (buildId: string) =>
    apiRequest<{
      conventions: Record<string, { value: unknown; confirmed_records: number }>;
      examples: Record<
        string,
        Array<{ record_id: string; value: unknown; similarity: number; excerpt: string }>
      >;
      reset_at?: string | null;
      convention_count: number;
      example_count: number;
    }>(`${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/editorial-memory`, {
      method: "DELETE",
    }),
};
