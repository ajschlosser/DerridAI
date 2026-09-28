/* Copyright 2026 Aaron John Schlosser, PhD. */
/** Internal type. DO NOT USE DIRECTLY. */
type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
/** Internal type. DO NOT USE DIRECTLY. */
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
import { DocumentTypeDecoration } from '@graphql-typed-document-node/core';
export type Maybe<T> = T | null;
export type InputMaybe<T> = Maybe<T>;
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
  ID: { input: string; output: string; }
  String: { input: string; output: string; }
  Boolean: { input: boolean; output: boolean; }
  Int: { input: number; output: number; }
  Float: { input: number; output: number; }
  /** The `JSON` scalar type represents JSON values as specified by [ECMA-404](https://ecma-international.org/wp-content/uploads/ECMA-404_2nd_edition_december_2017.pdf). */
  JSON: { input: unknown; output: unknown; }
};

/** The normative cELF 1.0 type graph (same payload as GET /api/derridai/model). */
export type CelfModel = {
  edges: Array<CelfRelationship>;
  nodes: Array<CelfObjectType>;
  specification_version: Scalars['String']['output'];
};

/** A normative cELF object type. */
export type CelfObjectType = {
  label: Scalars['String']['output'];
  normative: Scalars['Boolean']['output'];
  persistence: Scalars['String']['output'];
  profile: Scalars['String']['output'];
  type: Scalars['String']['output'];
};

/** A normative, walkable relationship between cELF object types. */
export type CelfRelationship = {
  id: Scalars['String']['output'];
  inverse_relation: Scalars['String']['output'];
  normative: Scalars['Boolean']['output'];
  profile: Scalars['String']['output'];
  relation: Scalars['String']['output'];
  source_cardinality: Scalars['String']['output'];
  source_type: Scalars['String']['output'];
  target_cardinality: Scalars['String']['output'];
  target_type: Scalars['String']['output'];
};

/** One PDF Corpus Builder build's reviewable Records (REST: /api/pdf/corpus-builds/{id}). */
export type CorpusBuildReview = {
  build_id: Scalars['String']['output'];
  /** Build-wide observed metadata values, optionally narrowed to specific fields. */
  metadata_facets: Scalars['JSON']['output'];
  /** One reviewer-presented Record (REST: full Record from the review page). */
  record: CorpusRecord;
  /** Reviewer-presented Records, in the order requested (missing ids come back null). */
  records: Array<Maybe<CorpusRecord>>;
  /** The paged, filtered review queue (REST: GET /api/pdf/corpus-builds/{id}/records). */
  review_queue: CorpusReviewQueuePage;
  /** Queue-row projections for specific Records, in the order requested. */
  rows: Array<Maybe<CorpusQueueRow>>;
};


/** One PDF Corpus Builder build's reviewable Records (REST: /api/pdf/corpus-builds/{id}). */
export type CorpusBuildReviewMetadata_FacetsArgs = {
  fields?: InputMaybe<Array<Scalars['String']['input']>>;
};


/** One PDF Corpus Builder build's reviewable Records (REST: /api/pdf/corpus-builds/{id}). */
export type CorpusBuildReviewRecordArgs = {
  record_id: Scalars['String']['input'];
};


/** One PDF Corpus Builder build's reviewable Records (REST: /api/pdf/corpus-builds/{id}). */
export type CorpusBuildReviewRecordsArgs = {
  record_ids: Array<Scalars['String']['input']>;
};


/** One PDF Corpus Builder build's reviewable Records (REST: /api/pdf/corpus-builds/{id}). */
export type CorpusBuildReviewReview_QueueArgs = {
  disposition?: InputMaybe<Scalars['String']['input']>;
  limit?: Scalars['Int']['input'];
  metadata_incomplete?: InputMaybe<Scalars['Boolean']['input']>;
  needs_review?: InputMaybe<Scalars['Boolean']['input']>;
  offset?: Scalars['Int']['input'];
  query?: Scalars['String']['input'];
  review_queue?: InputMaybe<Scalars['String']['input']>;
  source_problem?: InputMaybe<Scalars['Boolean']['input']>;
};


/** One PDF Corpus Builder build's reviewable Records (REST: /api/pdf/corpus-builds/{id}). */
export type CorpusBuildReviewRowsArgs = {
  record_ids: Array<Scalars['String']['input']>;
};

/** Build-wide review-queue counts by state. */
export type CorpusQueueCounts = {
  accepted: Scalars['Int']['output'];
  all: Scalars['Int']['output'];
  issues: Scalars['Int']['output'];
  metadata: Scalars['Int']['output'];
  pending: Scalars['Int']['output'];
  preparing: Scalars['Int']['output'];
  ready: Scalars['Int']['output'];
  rejected: Scalars['Int']['output'];
  source: Scalars['Int']['output'];
  topology: Scalars['Int']['output'];
};

/** One review-queue row: identifiers, page labels, review state and a short preview. Never the full text or metadata (REST: GET /api/pdf/corpus-builds/{id}/records, each `items` entry). */
export type CorpusQueueRow = {
  metadata_complete: Scalars['Boolean']['output'];
  metadata_llm_processed: Scalars['Boolean']['output'];
  needs_review: Scalars['Boolean']['output'];
  page_end?: Maybe<Scalars['String']['output']>;
  page_start?: Maybe<Scalars['String']['output']>;
  record_id: Scalars['String']['output'];
  record_revision?: Maybe<Scalars['Int']['output']>;
  review_disposition?: Maybe<Scalars['String']['output']>;
  review_issue_codes: Array<Scalars['String']['output']>;
  review_state?: Maybe<Scalars['String']['output']>;
  source_quality_issues: Scalars['Boolean']['output'];
  text_length: Scalars['Int']['output'];
  text_preview: Scalars['String']['output'];
};

/** A reviewer-presented Corpus Builder Record. `review_document` is transitional: the review panels still consume the full presented Record as JSON; prefer the typed fields above where they exist. */
export type CorpusRecord = {
  record_id: Scalars['String']['output'];
  record_revision?: Maybe<Scalars['Int']['output']>;
  review_disposition?: Maybe<Scalars['String']['output']>;
  review_document: Scalars['JSON']['output'];
  review_state?: Maybe<Scalars['String']['output']>;
  text: Scalars['String']['output'];
  work?: Maybe<Scalars['String']['output']>;
};

/** One page of the review queue: rows, total, and build-wide counts. */
export type CorpusReviewQueuePage = {
  items: Array<CorpusQueueRow>;
  limit: Scalars['Int']['output'];
  offset: Scalars['Int']['output'];
  queue_counts: CorpusQueueCounts;
  total: Scalars['Int']['output'];
};

/** A revision-bound evidence locator. */
export type EvidenceRef = {
  evidence_ref_id: Scalars['String']['output'];
  locator_kind?: Maybe<Scalars['String']['output']>;
  record_id?: Maybe<Scalars['String']['output']>;
  record_revision?: Maybe<Scalars['Int']['output']>;
  source_document_id?: Maybe<Scalars['String']['output']>;
};

/** One field value with independent derivation, evaluation and authority. A value is never exposed without the provenance dimensions that qualify it. */
export type FieldAssertion = {
  actor?: Maybe<Scalars['String']['output']>;
  assertion_id: Scalars['String']['output'];
  authority_status?: Maybe<Scalars['String']['output']>;
  confidence?: Maybe<Scalars['Float']['output']>;
  created_at?: Maybe<Scalars['String']['output']>;
  derivation_method?: Maybe<Scalars['String']['output']>;
  evaluation_status?: Maybe<Scalars['String']['output']>;
  evidence?: Maybe<Scalars['JSON']['output']>;
  field_id?: Maybe<Scalars['String']['output']>;
  field_name?: Maybe<Scalars['String']['output']>;
  /** Whether this is the field's selected current assertion. */
  is_current: Scalars['Boolean']['output'];
  method?: Maybe<Scalars['String']['output']>;
  model?: Maybe<Scalars['String']['output']>;
  reason?: Maybe<Scalars['String']['output']>;
  record_revision?: Maybe<Scalars['Int']['output']>;
  run_id?: Maybe<Scalars['String']['output']>;
  supersedes_assertion_id?: Maybe<Scalars['String']['output']>;
  /** Schema-defined value; arbitrary by design. */
  value?: Maybe<Scalars['JSON']['output']>;
  value_status?: Maybe<Scalars['String']['output']>;
};

/** A claim produced by a research run, owner-scoped. */
export type GeneratedClaim = {
  answer_end?: Maybe<Scalars['Int']['output']>;
  answer_start?: Maybe<Scalars['Int']['output']>;
  claim_id: Scalars['String']['output'];
  claim_text: Scalars['String']['output'];
  created_at?: Maybe<Scalars['String']['output']>;
  response_record_id?: Maybe<Scalars['String']['output']>;
  run_id?: Maybe<Scalars['String']['output']>;
  /** Advisory validated-claim precedents (REST: GET /api/derridai/claims/{id}/similar). */
  similar_validated_claims: Array<SimilarValidatedClaim>;
  /** Durable support bindings for this claim (batched per request). */
  support_bindings: Array<SupportBinding>;
  validated_at?: Maybe<Scalars['String']['output']>;
  validated_by?: Maybe<Scalars['String']['output']>;
  validation_status: Scalars['String']['output'];
};


/** A claim produced by a research run, owner-scoped. */
export type GeneratedClaimSimilar_Validated_ClaimsArgs = {
  limit?: Scalars['Int']['input'];
};

/** One reviewed metadata exemplar (REST: GET /api/system/data/metadata-exemplars rows). */
export type MetadataExemplar = {
  assertion_status?: Maybe<Scalars['String']['output']>;
  context_text: Scalars['String']['output'];
  evidence_block_ids: Scalars['JSON']['output'];
  evidence_hash?: Maybe<Scalars['String']['output']>;
  exemplar_id: Scalars['String']['output'];
  field_name?: Maybe<Scalars['String']['output']>;
  field_value?: Maybe<Scalars['JSON']['output']>;
  kind: Scalars['String']['output'];
  language?: Maybe<Scalars['String']['output']>;
  record_id?: Maybe<Scalars['String']['output']>;
  record_revision?: Maybe<Scalars['Int']['output']>;
  region_type?: Maybe<Scalars['String']['output']>;
  schema_id?: Maybe<Scalars['String']['output']>;
  schema_version?: Maybe<Scalars['String']['output']>;
  scope_id?: Maybe<Scalars['String']['output']>;
  source_document_id?: Maybe<Scalars['String']['output']>;
};

/** Distinct values observed across the current exemplar collection, for filter UIs. */
export type MetadataExemplarFacets = {
  fields: Array<Scalars['String']['output']>;
  kinds: Array<Scalars['String']['output']>;
  languages: Array<Scalars['String']['output']>;
  schemas: Array<Scalars['String']['output']>;
  scopes: Array<Scalars['String']['output']>;
};

/** A page of metadata exemplars. `exists=false` means the projection has not run yet. */
export type MetadataExemplarPage = {
  count: Scalars['Int']['output'];
  exists: Scalars['Boolean']['output'];
  facets: MetadataExemplarFacets;
  limit: Scalars['Int']['output'];
  offset: Scalars['Int']['output'];
  /** Unprojected reviewed-metadata work, with the most recent failure per build. */
  projection_backlog: Scalars['JSON']['output'];
  rows: Array<MetadataExemplar>;
};

/** Read-only cELF queries. Commands are REST; live events are WebSocket. */
export type Query = {
  /** The normative cELF type graph (REST: GET /api/derridai/model). */
  celf_model: CelfModel;
  /** A PDF Corpus Builder build by id (REST: GET /api/pdf/corpus-builds/{id}). */
  corpus_build: CorpusBuildReview;
  /** One owner-scoped generated claim. */
  generated_claim: GeneratedClaim;
  /** Progressive metadata exemplars (REST: GET /api/system/data/metadata-exemplars). */
  metadata_exemplars: MetadataExemplarPage;
  /** Walkable instance graph around one Record (REST: POST /api/derridai/graph/record). `record` is the caller's local Record snapshot; claims and support are joined server-side. */
  record_graph: ResearchObjectGraph;
  /** One Research run with its answer and cited evidence. */
  research_run: ResearchRun;
  /** A vector store by name (REST: GET /api/stores/{name}). */
  vector_store: VectorStore;
};


/** Read-only cELF queries. Commands are REST; live events are WebSocket. */
export type QueryCorpus_BuildArgs = {
  build_id: Scalars['String']['input'];
};


/** Read-only cELF queries. Commands are REST; live events are WebSocket. */
export type QueryGenerated_ClaimArgs = {
  claim_id: Scalars['String']['input'];
};


/** Read-only cELF queries. Commands are REST; live events are WebSocket. */
export type QueryMetadata_ExemplarsArgs = {
  field?: Scalars['String']['input'];
  kind?: Scalars['String']['input'];
  language?: Scalars['String']['input'];
  limit?: Scalars['Int']['input'];
  offset?: Scalars['Int']['input'];
  record_id?: Scalars['String']['input'];
  schema_id?: Scalars['String']['input'];
  scope_id?: Scalars['String']['input'];
};


/** Read-only cELF queries. Commands are REST; live events are WebSocket. */
export type QueryRecord_GraphArgs = {
  include_assertion_history?: Scalars['Boolean']['input'];
  record: Scalars['JSON']['input'];
};


/** Read-only cELF queries. Commands are REST; live events are WebSocket. */
export type QueryResearch_RunArgs = {
  run_id: Scalars['String']['input'];
};


/** Read-only cELF queries. Commands are REST; live events are WebSocket. */
export type QueryVector_StoreArgs = {
  name: Scalars['String']['input'];
};

/** An edge of the instance graph, annotated from the normative relationship registry. */
export type ResearchObjectEdge = {
  id: Scalars['String']['output'];
  inverse_relation: Scalars['String']['output'];
  normative: Scalars['Boolean']['output'];
  profile?: Maybe<Scalars['String']['output']>;
  relation: Scalars['String']['output'];
  source: Scalars['String']['output'];
  source_cardinality?: Maybe<Scalars['String']['output']>;
  status?: Maybe<Scalars['String']['output']>;
  target: Scalars['String']['output'];
  target_cardinality?: Maybe<Scalars['String']['output']>;
};

/** A finite, re-centerable cELF instance graph around one Record. */
export type ResearchObjectGraph = {
  edges: Array<ResearchObjectEdge>;
  hidden_assertion_count: Scalars['Int']['output'];
  nodes: Array<ResearchObjectNode>;
  /** client_snapshot: Record state came from the caller; claims/support are server-owned. */
  record_state_origin: Scalars['String']['output'];
  root_id: Scalars['String']['output'];
  specification_version: Scalars['String']['output'];
};

/** A node of the instance graph. Typed projections resolve for their object_type only. */
export type ResearchObjectNode = {
  details: Scalars['JSON']['output'];
  evidence_ref?: Maybe<EvidenceRef>;
  field_assertion?: Maybe<FieldAssertion>;
  /** The owner-scoped durable claim behind a GeneratedClaim node (batched). */
  generated_claim?: Maybe<GeneratedClaim>;
  id: Scalars['String']['output'];
  label: Scalars['String']['output'];
  /** materialized | embedded | reference | derived_view. Derived views are never canonical. */
  materialization: Scalars['String']['output'];
  object_id: Scalars['String']['output'];
  object_type: Scalars['String']['output'];
  source_span?: Maybe<SourceSpan>;
  status?: Maybe<Scalars['String']['output']>;
  summary: Scalars['String']['output'];
};

/** A Research (RAG) run: its answer and cited evidence (REST: GET /api/jobs/{id}). */
export type ResearchRun = {
  answer?: Maybe<Scalars['String']['output']>;
  created_at?: Maybe<Scalars['String']['output']>;
  /** Cited evidence entries. Researcher-owned runs already have record text summarized. */
  evidence: Scalars['JSON']['output'];
  finished_at?: Maybe<Scalars['String']['output']>;
  /** Generated claims produced by this run (administrator-only). */
  generated_claims: Array<GeneratedClaim>;
  model?: Maybe<Scalars['String']['output']>;
  owner?: Maybe<Scalars['String']['output']>;
  prompt?: Maybe<Scalars['String']['output']>;
  provider?: Maybe<Scalars['String']['output']>;
  run_id: Scalars['String']['output'];
  stage?: Maybe<Scalars['String']['output']>;
  started_at?: Maybe<Scalars['String']['output']>;
  status: Scalars['String']['output'];
  warnings: Array<Scalars['String']['output']>;
};

/** Record support carried by an advisory validated-claim precedent. */
export type SimilarClaimSupport = {
  record_id: Scalars['String']['output'];
  record_revision?: Maybe<Scalars['Int']['output']>;
  relation?: Maybe<Scalars['String']['output']>;
  /** Checked attribution snapshot (speaker, position_holder, …). */
  semantic: Scalars['JSON']['output'];
};

/** Advisory precedent only: similarity never asserts evidentiary support. */
export type SimilarValidatedClaim = {
  advisory: Scalars['Boolean']['output'];
  claim_id: Scalars['String']['output'];
  claim_text: Scalars['String']['output'];
  similarity: Scalars['Float']['output'];
  support: Array<SimilarClaimSupport>;
  validated_at?: Maybe<Scalars['String']['output']>;
  validated_by?: Maybe<Scalars['String']['output']>;
};

/** A medium-aware documentary locator. Audio spans use time and speaker, never PDF pages. */
export type SourceSpan = {
  character_end?: Maybe<Scalars['Int']['output']>;
  character_start?: Maybe<Scalars['Int']['output']>;
  locator_kind?: Maybe<Scalars['String']['output']>;
  physical_page_end?: Maybe<Scalars['Int']['output']>;
  physical_page_start?: Maybe<Scalars['Int']['output']>;
  printed_page_end?: Maybe<Scalars['String']['output']>;
  printed_page_start?: Maybe<Scalars['String']['output']>;
  source_document_id?: Maybe<Scalars['String']['output']>;
  source_span_id?: Maybe<Scalars['String']['output']>;
  source_unit_ids: Array<Scalars['String']['output']>;
  speaker?: Maybe<Scalars['String']['output']>;
  time_end?: Maybe<Scalars['Float']['output']>;
  time_start?: Maybe<Scalars['Float']['output']>;
};

/** A durable support relation between a generated claim and Record evidence. */
export type SupportBinding = {
  /** Deterministic citation rendered when bound. */
  citation?: Maybe<Scalars['JSON']['output']>;
  claim_id: Scalars['String']['output'];
  created_at?: Maybe<Scalars['String']['output']>;
  record_id: Scalars['String']['output'];
  record_revision?: Maybe<Scalars['Int']['output']>;
  relation: Scalars['String']['output'];
  source_document_id?: Maybe<Scalars['String']['output']>;
  /** Medium-aware source spans bound as evidence. */
  source_spans: Array<SourceSpan>;
  support_binding_id: Scalars['String']['output'];
  /** unvalidated | validated | stale | rejected | unresolved. Stale/unresolved stay visible. */
  validation_status: Scalars['String']['output'];
};

/** A full vector-store Record projection. Derived, never canonical: `graph` builds a walkable cELF graph from this stored record's own fields, which is weaker provenance than a `record_graph` built from the canonical corpus Record (materialization: vector_projection). */
export type VectorRecord = {
  chroma_id: Scalars['String']['output'];
  /** The full stored record, already access-scoped (researcher-text-summarized when applicable). */
  document: Scalars['JSON']['output'];
  /** record_graph built from this stored record's own fields (record_state_origin: vector_projection). */
  graph: ResearchObjectGraph;
  materialization: Scalars['String']['output'];
  record_id?: Maybe<Scalars['String']['output']>;
  text: Scalars['String']['output'];
  /** True when text was shortened by the researcher-text policy (REST: summarize_record). */
  text_summarized: Scalars['Boolean']['output'];
  work?: Maybe<Scalars['String']['output']>;
};

/** A page of vector-store table rows (REST: GET /api/stores/{name}/records). */
export type VectorRecordPage = {
  count: Scalars['Int']['output'];
  items: Array<VectorRecordRow>;
  limit: Scalars['Int']['output'];
  offset: Scalars['Int']['output'];
  work?: Maybe<Scalars['String']['output']>;
};

/** One vector-store table row: identifiers, work, pages and a short preview. Never the full text (materialization: vector_projection). */
export type VectorRecordRow = {
  chroma_id: Scalars['String']['output'];
  materialization: Scalars['String']['output'];
  page_end?: Maybe<Scalars['String']['output']>;
  page_start?: Maybe<Scalars['String']['output']>;
  record_id?: Maybe<Scalars['String']['output']>;
  text_preview: Scalars['String']['output'];
  work?: Maybe<Scalars['String']['output']>;
};

/** A Chroma-backed vector store: derived corpus projection, never canonical. */
export type VectorStore = {
  name: Scalars['String']['output'];
  /** One vector-store record by chroma_id (REST: GET /api/stores/{name}/records/{id}). */
  record?: Maybe<VectorRecord>;
  /** A page of vector-store records (REST: GET /api/stores/{name}/records). */
  records: VectorRecordPage;
  /** Per-work aggregate stats (REST: GET /api/stores/{name}/works). */
  works: Array<VectorWorkStat>;
};


/** A Chroma-backed vector store: derived corpus projection, never canonical. */
export type VectorStoreRecordArgs = {
  chroma_id: Scalars['String']['input'];
};


/** A Chroma-backed vector store: derived corpus projection, never canonical. */
export type VectorStoreRecordsArgs = {
  limit?: Scalars['Int']['input'];
  offset?: Scalars['Int']['input'];
  work?: InputMaybe<Scalars['String']['input']>;
};

/** Aggregate stats for one work across the store (REST: GET /api/stores/{name}/works). */
export type VectorWorkStat = {
  average_record_length: Scalars['Int']['output'];
  count: Scalars['Int']['output'];
  /** Other fields observed for the work (mixed values, edition, …). */
  details: Scalars['JSON']['output'];
  total_words: Scalars['Int']['output'];
  work: Scalars['String']['output'];
};

export type CelfModelQueryVariables = Exact<{ [key: string]: never; }>;


export type CelfModelQuery = { celf_model: { specification_version: string, nodes: Array<{ type: string, profile: string, persistence: string, label: string, normative: boolean }>, edges: Array<{ id: string, source_type: string, target_type: string, relation: string, inverse_relation: string, source_cardinality: string, target_cardinality: string, profile: string, normative: boolean }> } };

export type RecordGraphQueryVariables = Exact<{
  record: unknown;
  include_assertion_history?: boolean;
}>;


export type RecordGraphQuery = { record_graph: { specification_version: string, root_id: string, hidden_assertion_count: number, record_state_origin: string, nodes: Array<{ id: string, object_type: string, object_id: string, label: string, summary: string, materialization: string, status: string | null, details: unknown, field_assertion: { assertion_id: string, field_id: string | null, field_name: string | null, value: unknown, derivation_method: string | null, evaluation_status: string | null, authority_status: string | null, value_status: string | null, confidence: number | null, reason: string | null, method: string | null, actor: string | null, model: string | null, run_id: string | null, record_revision: number | null, evidence: unknown, created_at: string | null, supersedes_assertion_id: string | null, is_current: boolean } | null, source_span: { source_document_id: string | null, source_span_id: string | null, source_unit_ids: Array<string>, locator_kind: string | null, physical_page_start: number | null, physical_page_end: number | null, printed_page_start: string | null, printed_page_end: string | null, character_start: number | null, character_end: number | null, time_start: number | null, time_end: number | null, speaker: string | null } | null, evidence_ref: { evidence_ref_id: string, locator_kind: string | null, record_id: string | null, record_revision: number | null, source_document_id: string | null } | null, generated_claim: { claim_id: string, claim_text: string, validation_status: string } | null }>, edges: Array<{ id: string, source: string, target: string, relation: string, inverse_relation: string, normative: boolean, source_cardinality: string | null, target_cardinality: string | null, profile: string | null, status: string | null }> } };

export type SimilarValidatedClaimsQueryVariables = Exact<{
  claim_id: string;
  limit: number;
}>;


export type SimilarValidatedClaimsQuery = { generated_claim: { claim_id: string, similar_validated_claims: Array<{ claim_id: string, claim_text: string, similarity: number, validated_by: string | null, validated_at: string | null, advisory: boolean, support: Array<{ record_id: string, record_revision: number | null, relation: string | null, semantic: unknown }> }> } };

export type CorpusMetadataFacetsQueryVariables = Exact<{
  build_id: string;
  fields?: Array<string> | string | null | undefined;
}>;


export type CorpusMetadataFacetsQuery = { corpus_build: { metadata_facets: unknown } };

export type CorpusQueueRowFieldsFragment = { record_id: string, record_revision: number | null, page_start: string | null, page_end: string | null, text_length: number, text_preview: string, review_state: string | null, review_disposition: string | null, review_issue_codes: Array<string>, metadata_llm_processed: boolean, needs_review: boolean, source_quality_issues: boolean, metadata_complete: boolean };

export type CorpusQueueRowsQueryVariables = Exact<{
  build_id: string;
  record_ids: Array<string> | string;
}>;


export type CorpusQueueRowsQuery = { corpus_build: { rows: Array<{ record_id: string, record_revision: number | null, page_start: string | null, page_end: string | null, text_length: number, text_preview: string, review_state: string | null, review_disposition: string | null, review_issue_codes: Array<string>, metadata_llm_processed: boolean, needs_review: boolean, source_quality_issues: boolean, metadata_complete: boolean } | null> } };

export type CorpusQueueTextsQueryVariables = Exact<{
  build_id: string;
  record_ids: Array<string> | string;
}>;


export type CorpusQueueTextsQuery = { corpus_build: { records: Array<{ record_id: string, text: string } | null> } };

export type CorpusReviewQueueQueryVariables = Exact<{
  build_id: string;
  offset?: number | null | undefined;
  limit?: number | null | undefined;
  needs_review?: boolean | null | undefined;
  disposition?: string | null | undefined;
  metadata_incomplete?: boolean | null | undefined;
  source_problem?: boolean | null | undefined;
  review_queue?: string | null | undefined;
  query?: string | null | undefined;
}>;


export type CorpusReviewQueueQuery = { corpus_build: { review_queue: { total: number, offset: number, limit: number, items: Array<{ record_id: string, record_revision: number | null, page_start: string | null, page_end: string | null, text_length: number, text_preview: string, review_state: string | null, review_disposition: string | null, review_issue_codes: Array<string>, metadata_llm_processed: boolean, needs_review: boolean, source_quality_issues: boolean, metadata_complete: boolean }>, queue_counts: { all: number, ready: number, preparing: number, issues: number, metadata: number, topology: number, source: number, accepted: number, rejected: number, pending: number } } } };

export type CorpusReviewRecordsQueryVariables = Exact<{
  build_id: string;
  record_ids: Array<string> | string;
}>;


export type CorpusReviewRecordsQuery = { corpus_build: { records: Array<{ record_id: string, record_revision: number | null, review_document: unknown } | null> } };

export type StoredRecordTraceQueryVariables = Exact<{
  store: string;
  chroma_id: string;
}>;


export type StoredRecordTraceQuery = { vector_store: { record: { document: unknown, graph: { specification_version: string, root_id: string, hidden_assertion_count: number, record_state_origin: string, nodes: Array<{ id: string, object_type: string, object_id: string, label: string, summary: string, materialization: string, status: string | null, details: unknown, field_assertion: { assertion_id: string, field_id: string | null, field_name: string | null, value: unknown, derivation_method: string | null, evaluation_status: string | null, authority_status: string | null, value_status: string | null, confidence: number | null, reason: string | null, method: string | null, actor: string | null, model: string | null, run_id: string | null, record_revision: number | null, evidence: unknown, created_at: string | null, supersedes_assertion_id: string | null, is_current: boolean } | null, source_span: { source_document_id: string | null, source_span_id: string | null, source_unit_ids: Array<string>, locator_kind: string | null, physical_page_start: number | null, physical_page_end: number | null, printed_page_start: string | null, printed_page_end: string | null, character_start: number | null, character_end: number | null, time_start: number | null, time_end: number | null, speaker: string | null } | null, evidence_ref: { evidence_ref_id: string, locator_kind: string | null, record_id: string | null, record_revision: number | null, source_document_id: string | null } | null, generated_claim: { claim_id: string, claim_text: string, validation_status: string } | null }>, edges: Array<{ id: string, source: string, target: string, relation: string, inverse_relation: string, normative: boolean, source_cardinality: string | null, target_cardinality: string | null, profile: string | null, status: string | null }> } } | null } };

export type VectorRecordRowFieldsFragment = { chroma_id: string, record_id: string | null, work: string | null, page_start: string | null, page_end: string | null, text_preview: string };

export type VectorStoreBrowseQueryVariables = Exact<{
  name: string;
  includeRecords: boolean;
  offset: number;
  limit: number;
  work?: string | null | undefined;
}>;


export type VectorStoreBrowseQuery = { vector_store: { works: Array<{ work: string, count: number, total_words: number, average_record_length: number }>, records?: { count: number, offset: number, limit: number, items: Array<{ chroma_id: string, record_id: string | null, work: string | null, page_start: string | null, page_end: string | null, text_preview: string }> } } };

export type ResearchObjectGraphFieldsFragment = { specification_version: string, root_id: string, hidden_assertion_count: number, record_state_origin: string, nodes: Array<{ id: string, object_type: string, object_id: string, label: string, summary: string, materialization: string, status: string | null, details: unknown, field_assertion: { assertion_id: string, field_id: string | null, field_name: string | null, value: unknown, derivation_method: string | null, evaluation_status: string | null, authority_status: string | null, value_status: string | null, confidence: number | null, reason: string | null, method: string | null, actor: string | null, model: string | null, run_id: string | null, record_revision: number | null, evidence: unknown, created_at: string | null, supersedes_assertion_id: string | null, is_current: boolean } | null, source_span: { source_document_id: string | null, source_span_id: string | null, source_unit_ids: Array<string>, locator_kind: string | null, physical_page_start: number | null, physical_page_end: number | null, printed_page_start: string | null, printed_page_end: string | null, character_start: number | null, character_end: number | null, time_start: number | null, time_end: number | null, speaker: string | null } | null, evidence_ref: { evidence_ref_id: string, locator_kind: string | null, record_id: string | null, record_revision: number | null, source_document_id: string | null } | null, generated_claim: { claim_id: string, claim_text: string, validation_status: string } | null }>, edges: Array<{ id: string, source: string, target: string, relation: string, inverse_relation: string, normative: boolean, source_cardinality: string | null, target_cardinality: string | null, profile: string | null, status: string | null }> };

export class TypedDocumentString<TResult, TVariables>
  extends String
  implements DocumentTypeDecoration<TResult, TVariables>
{
  __apiType?: NonNullable<DocumentTypeDecoration<TResult, TVariables>['__apiType']>;
  private value: string;
  public __meta__?: Record<string, any> | undefined;

  constructor(value: string, __meta__?: Record<string, any> | undefined) {
    super(value);
    this.value = value;
    this.__meta__ = __meta__;
  }

  override toString(): string & DocumentTypeDecoration<TResult, TVariables> {
    return this.value;
  }
}
export const CorpusQueueRowFieldsFragmentDoc = new TypedDocumentString(`
    fragment CorpusQueueRowFields on CorpusQueueRow {
  record_id
  record_revision
  page_start
  page_end
  text_length
  text_preview
  review_state
  review_disposition
  review_issue_codes
  metadata_llm_processed
  needs_review
  source_quality_issues
  metadata_complete
}
    `, {"fragmentName":"CorpusQueueRowFields"}) as unknown as TypedDocumentString<CorpusQueueRowFieldsFragment, unknown>;
export const VectorRecordRowFieldsFragmentDoc = new TypedDocumentString(`
    fragment VectorRecordRowFields on VectorRecordRow {
  chroma_id
  record_id
  work
  page_start
  page_end
  text_preview
}
    `, {"fragmentName":"VectorRecordRowFields"}) as unknown as TypedDocumentString<VectorRecordRowFieldsFragment, unknown>;
export const ResearchObjectGraphFieldsFragmentDoc = new TypedDocumentString(`
    fragment ResearchObjectGraphFields on ResearchObjectGraph {
  specification_version
  root_id
  hidden_assertion_count
  record_state_origin
  nodes {
    id
    object_type
    object_id
    label
    summary
    materialization
    status
    details
    field_assertion {
      assertion_id
      field_id
      field_name
      value
      derivation_method
      evaluation_status
      authority_status
      value_status
      confidence
      reason
      method
      actor
      model
      run_id
      record_revision
      evidence
      created_at
      supersedes_assertion_id
      is_current
    }
    source_span {
      source_document_id
      source_span_id
      source_unit_ids
      locator_kind
      physical_page_start
      physical_page_end
      printed_page_start
      printed_page_end
      character_start
      character_end
      time_start
      time_end
      speaker
    }
    evidence_ref {
      evidence_ref_id
      locator_kind
      record_id
      record_revision
      source_document_id
    }
    generated_claim {
      claim_id
      claim_text
      validation_status
    }
  }
  edges {
    id
    source
    target
    relation
    inverse_relation
    normative
    source_cardinality
    target_cardinality
    profile
    status
  }
}
    `, {"fragmentName":"ResearchObjectGraphFields"}) as unknown as TypedDocumentString<ResearchObjectGraphFieldsFragment, unknown>;
export const CelfModelDocument = new TypedDocumentString(`
    query CelfModel {
  celf_model {
    specification_version
    nodes {
      type
      profile
      persistence
      label
      normative
    }
    edges {
      id
      source_type
      target_type
      relation
      inverse_relation
      source_cardinality
      target_cardinality
      profile
      normative
    }
  }
}
    `) as unknown as TypedDocumentString<CelfModelQuery, CelfModelQueryVariables>;
export const RecordGraphDocument = new TypedDocumentString(`
    query RecordGraph($record: JSON!, $include_assertion_history: Boolean! = false) {
  record_graph(
    record: $record
    include_assertion_history: $include_assertion_history
  ) {
    ...ResearchObjectGraphFields
  }
}
    fragment ResearchObjectGraphFields on ResearchObjectGraph {
  specification_version
  root_id
  hidden_assertion_count
  record_state_origin
  nodes {
    id
    object_type
    object_id
    label
    summary
    materialization
    status
    details
    field_assertion {
      assertion_id
      field_id
      field_name
      value
      derivation_method
      evaluation_status
      authority_status
      value_status
      confidence
      reason
      method
      actor
      model
      run_id
      record_revision
      evidence
      created_at
      supersedes_assertion_id
      is_current
    }
    source_span {
      source_document_id
      source_span_id
      source_unit_ids
      locator_kind
      physical_page_start
      physical_page_end
      printed_page_start
      printed_page_end
      character_start
      character_end
      time_start
      time_end
      speaker
    }
    evidence_ref {
      evidence_ref_id
      locator_kind
      record_id
      record_revision
      source_document_id
    }
    generated_claim {
      claim_id
      claim_text
      validation_status
    }
  }
  edges {
    id
    source
    target
    relation
    inverse_relation
    normative
    source_cardinality
    target_cardinality
    profile
    status
  }
}`) as unknown as TypedDocumentString<RecordGraphQuery, RecordGraphQueryVariables>;
export const SimilarValidatedClaimsDocument = new TypedDocumentString(`
    query SimilarValidatedClaims($claim_id: String!, $limit: Int!) {
  generated_claim(claim_id: $claim_id) {
    claim_id
    similar_validated_claims(limit: $limit) {
      claim_id
      claim_text
      similarity
      validated_by
      validated_at
      advisory
      support {
        record_id
        record_revision
        relation
        semantic
      }
    }
  }
}
    `) as unknown as TypedDocumentString<SimilarValidatedClaimsQuery, SimilarValidatedClaimsQueryVariables>;
export const CorpusMetadataFacetsDocument = new TypedDocumentString(`
    query CorpusMetadataFacets($build_id: String!, $fields: [String!]) {
  corpus_build(build_id: $build_id) {
    metadata_facets(fields: $fields)
  }
}
    `) as unknown as TypedDocumentString<CorpusMetadataFacetsQuery, CorpusMetadataFacetsQueryVariables>;
export const CorpusQueueRowsDocument = new TypedDocumentString(`
    query CorpusQueueRows($build_id: String!, $record_ids: [String!]!) {
  corpus_build(build_id: $build_id) {
    rows(record_ids: $record_ids) {
      ...CorpusQueueRowFields
    }
  }
}
    fragment CorpusQueueRowFields on CorpusQueueRow {
  record_id
  record_revision
  page_start
  page_end
  text_length
  text_preview
  review_state
  review_disposition
  review_issue_codes
  metadata_llm_processed
  needs_review
  source_quality_issues
  metadata_complete
}`) as unknown as TypedDocumentString<CorpusQueueRowsQuery, CorpusQueueRowsQueryVariables>;
export const CorpusQueueTextsDocument = new TypedDocumentString(`
    query CorpusQueueTexts($build_id: String!, $record_ids: [String!]!) {
  corpus_build(build_id: $build_id) {
    records(record_ids: $record_ids) {
      record_id
      text
    }
  }
}
    `) as unknown as TypedDocumentString<CorpusQueueTextsQuery, CorpusQueueTextsQueryVariables>;
export const CorpusReviewQueueDocument = new TypedDocumentString(`
    query CorpusReviewQueue($build_id: String!, $offset: Int = 0, $limit: Int = 50, $needs_review: Boolean, $disposition: String, $metadata_incomplete: Boolean, $source_problem: Boolean, $review_queue: String, $query: String = "") {
  corpus_build(build_id: $build_id) {
    review_queue(
      offset: $offset
      limit: $limit
      needs_review: $needs_review
      disposition: $disposition
      metadata_incomplete: $metadata_incomplete
      source_problem: $source_problem
      review_queue: $review_queue
      query: $query
    ) {
      items {
        ...CorpusQueueRowFields
      }
      total
      offset
      limit
      queue_counts {
        all
        ready
        preparing
        issues
        metadata
        topology
        source
        accepted
        rejected
        pending
      }
    }
  }
}
    fragment CorpusQueueRowFields on CorpusQueueRow {
  record_id
  record_revision
  page_start
  page_end
  text_length
  text_preview
  review_state
  review_disposition
  review_issue_codes
  metadata_llm_processed
  needs_review
  source_quality_issues
  metadata_complete
}`) as unknown as TypedDocumentString<CorpusReviewQueueQuery, CorpusReviewQueueQueryVariables>;
export const CorpusReviewRecordsDocument = new TypedDocumentString(`
    query CorpusReviewRecords($build_id: String!, $record_ids: [String!]!) {
  corpus_build(build_id: $build_id) {
    records(record_ids: $record_ids) {
      record_id
      record_revision
      review_document
    }
  }
}
    `) as unknown as TypedDocumentString<CorpusReviewRecordsQuery, CorpusReviewRecordsQueryVariables>;
export const StoredRecordTraceDocument = new TypedDocumentString(`
    query StoredRecordTrace($store: String!, $chroma_id: String!) {
  vector_store(name: $store) {
    record(chroma_id: $chroma_id) {
      document
      graph {
        ...ResearchObjectGraphFields
      }
    }
  }
}
    fragment ResearchObjectGraphFields on ResearchObjectGraph {
  specification_version
  root_id
  hidden_assertion_count
  record_state_origin
  nodes {
    id
    object_type
    object_id
    label
    summary
    materialization
    status
    details
    field_assertion {
      assertion_id
      field_id
      field_name
      value
      derivation_method
      evaluation_status
      authority_status
      value_status
      confidence
      reason
      method
      actor
      model
      run_id
      record_revision
      evidence
      created_at
      supersedes_assertion_id
      is_current
    }
    source_span {
      source_document_id
      source_span_id
      source_unit_ids
      locator_kind
      physical_page_start
      physical_page_end
      printed_page_start
      printed_page_end
      character_start
      character_end
      time_start
      time_end
      speaker
    }
    evidence_ref {
      evidence_ref_id
      locator_kind
      record_id
      record_revision
      source_document_id
    }
    generated_claim {
      claim_id
      claim_text
      validation_status
    }
  }
  edges {
    id
    source
    target
    relation
    inverse_relation
    normative
    source_cardinality
    target_cardinality
    profile
    status
  }
}`) as unknown as TypedDocumentString<StoredRecordTraceQuery, StoredRecordTraceQueryVariables>;
export const VectorStoreBrowseDocument = new TypedDocumentString(`
    query VectorStoreBrowse($name: String!, $includeRecords: Boolean!, $offset: Int!, $limit: Int!, $work: String) {
  vector_store(name: $name) {
    works {
      work
      count
      total_words
      average_record_length
    }
    records(offset: $offset, limit: $limit, work: $work) @include(if: $includeRecords) {
      items {
        ...VectorRecordRowFields
      }
      count
      offset
      limit
    }
  }
}
    fragment VectorRecordRowFields on VectorRecordRow {
  chroma_id
  record_id
  work
  page_start
  page_end
  text_preview
}`) as unknown as TypedDocumentString<VectorStoreBrowseQuery, VectorStoreBrowseQueryVariables>;