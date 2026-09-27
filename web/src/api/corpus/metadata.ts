/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "../http";
import type { CorpusBuild, CorpusRecord, EnrichmentMetrics, HumanEvidenceSource } from "./types";
import { LEGACY_CORPUS_BASE, legacyCorpusUrl } from "./compatibility";

export interface EvidenceSuggestion {
  block_id: string;
  reason: string;
  method: string;
  score?: number;
  /** LLM choices only: whether a deterministic text match also supports the block. */
  lexical_support?: boolean;
}

/** Authoritative state returned after one or several reviewer metadata decisions. */
export interface MetadataDecisionResult {
  applied: boolean;
  record: CorpusRecord;
  build: CorpusBuild;
  changed_fields: string[];
  /** Fields owed a blind second opinion: the answer was logged and the record left unchanged. */
  deferred_fields: string[];
  /** Non-fatal problems in derived memory; the decisions themselves were saved. */
  warnings: string[];
}

/** One reviewed precedent, exactly as metadata enrichment would see it. */
export interface MetadataPrecedent {
  exemplar_id?: string;
  record_id: string;
  record_revision?: number | null;
  value: unknown;
  /** Absent for an ordinary positive precedent. */
  kind?: "correction" | "absence";
  /** For a correction: the model value the reviewer rejected. */
  rejected_value?: unknown;
  similarity?: number;
  /** False for older decisions without reviewed evidence (record excerpt only). */
  evidence_bound: boolean;
  evidence?: string;
  excerpt?: string;
  /** Present only when the field's declared analogy conditions were compared and agree. */
  match?: { tier: "matched"; fields: string[] };
  /**
   * Blocks of the record under review ranked against this precedent's evidence. Advisory: they
   * bind nothing, and they never come from the precedent's own record.
   */
  candidate_source_units?: PrecedentCandidateUnit[];
}

/** One of this record's own source blocks that resembles a precedent's reviewed evidence. */
export interface PrecedentCandidateUnit {
  block_id: string;
  score: number;
  method: string;
  source_unit_id?: string;
  page?: number;
  printed_page_label?: string;
  start?: number;
  end?: number;
}

export interface MetadataPrecedents {
  field: string;
  record_id: string;
  /** "enrichment": kept from the last metadata enrichment and re-verified; "live": searched now. */
  source?: "enrichment" | "live";
  computed_at?: string;
  mode: "semantic" | "lexical" | "none";
  fallback_reason: string;
  /** Kept precedents that changed or are hidden from this reviewer since enrichment; not shown. */
  stale_count?: number;
  items: MetadataPrecedent[];
}

/** A reviewer-validated Research claim whose support cites a record. */
export interface RecordResearchClaim {
  claim_id: string;
  claim_text: string;
  run_id?: string | null;
  validated_by?: string | null;
  validated_at?: string | null;
  relation?: string | null;
  record_revision?: number | null;
  citation: { inline?: string; full?: string };
  /** "stale": bound to an earlier revision or source; never applied to the current text. */
  binding_status: "current" | "stale" | "unresolved";
}

const recordUrl = (buildId: string, recordId: string) =>
  `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}`;

export const corpusMetadataApi = {
  suggestEvidence: (buildId: string, recordId: string, field: string) =>
    apiRequest<{ items: EvidenceSuggestion[] }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/evidence-suggestions?field=${encodeURIComponent(field)}`,
    ),
  suggestEvidenceLlm: (
    buildId: string,
    recordId: string,
    field: string,
    request: Record<string, unknown>,
  ) =>
    apiRequest<{ items: EvidenceSuggestion[] }>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/evidence-suggestions/llm`,
      { method: "POST", body: JSON.stringify({ ...request, field }) },
    ),
  precedents: (buildId: string, recordId: string, field: string, refresh = false) =>
    apiRequest<MetadataPrecedents>(
      `${recordUrl(buildId, recordId)}/precedents?field=${encodeURIComponent(field)}${refresh ? "&refresh=true" : ""}`,
    ),
  /** Every field's precedents kept from the last enrichment; fields not kept are absent. */
  fieldPrecedents: (buildId: string, recordId: string) =>
    apiRequest<{ record_id: string; fields: Record<string, MetadataPrecedents> }>(
      `${recordUrl(buildId, recordId)}/field-precedents`,
    ),
  researchClaims: (buildId: string, recordId: string) =>
    apiRequest<{ items: RecordResearchClaim[] }>(`${recordUrl(buildId, recordId)}/research-claims`),
  metadataDecision: (
    buildId: string,
    recordId: string,
    field: string,
    value: unknown,
    expectedRevision?: number,
    confirmNoSupportedValue = false,
    evidenceBlockIds?: string[],
    humanSource?: HumanEvidenceSource,
  ) =>
    apiRequest<MetadataDecisionResult>(
      `${LEGACY_CORPUS_BASE}/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/metadata-decision`,
      {
        method: "POST",
        body: JSON.stringify({
          field,
          value,
          expected_revision: expectedRevision,
          confirm_no_supported_value: confirmNoSupportedValue,
          // Only sent when the reviewer saved with selected text as evidence.
          evidence_block_ids: evidenceBlockIds,
          // Only sent when the reviewer cites their own knowledge, or spans elsewhere in the same source.
          evidence_source: humanSource?.source,
          evidence_note: humanSource?.note,
          external_evidence_block_ids: humanSource?.externalBlockIds,
        }),
      },
    ),
  metadataDecisionBatch: (
    buildId: string,
    recordId: string,
    changes: Record<string, unknown>,
    expectedRevision?: number,
  ) =>
    apiRequest<MetadataDecisionResult>(
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
