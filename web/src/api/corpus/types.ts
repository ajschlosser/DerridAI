/* Copyright 2026 Aaron John Schlosser, PhD. */

import type { LayoutRegion } from "../../domain/documentLayoutRegions";

/** How printed page numbers are found in text sources: deterministic patterns, optionally then a model, or not at all. */
export interface PageDetectionRequest {
  mode: "auto" | "auto_llm" | "off";
  /** Provider profile the model-assisted step uses (only for `auto_llm`). */
  providerProfileId?: string;
  /**
   * The profile's connection, for a browser-held (administrator) profile the server cannot resolve by ID alone. Sent
   * the same way a build sends it; the server uses it for this request only.
   */
  connection?: { provider?: string; model?: string; base_url?: string; api_key?: string };
}

export type SourceUnitMode = "default" | "paragraph" | "line" | "sentence" | "chars" | "auto";

export interface SourceUnitPolicy {
  mode: SourceUnitMode;
  /** Documentary-language hint used for sentence/automatic orthographic segmentation. */
  language?: string;
  /** Characters per unit; only for mode "chars". */
  chars?: number;
  /** Group this many paragraphs or sentences into one unit (1 or absent = no grouping). */
  per?: number;
}

export interface SourceUnitPreview {
  policy: SourceUnitPolicy;
  unit_count: number;
  source_block_count: number;
  median_chars: number;
  max_chars: number;
  min_chars: number;
  language_segmentation?: {
    language: string;
    profile: string;
    script: string;
    engine: string;
    language_source: "declared" | "script_inference" | "undetermined";
    uses_case: boolean;
  };
  sample: { block_id: string; page: number | null; text: string }[];
}

export interface PdfAsset {
  /** The asset this one was derived from, and the unit policy that derived it. */
  derived_from_asset_id?: string;
  unit_policy?: SourceUnitPolicy;
  unit_segmentation?: SourceUnitPreview["language_segmentation"];
  asset_id: string;
  sha256: string;
  filename: string;
  main_text_start_inference?: {
    page: number | null;
    confidence: number;
    clues: { kind: string; detail: string }[];
    offered: boolean;
  };
  created_at: string;
  page_count: number;
  block_count: number;
  /** Deterministic page-number detection for text sources (absent for PDFs and audio). */
  page_number_detection?: {
    status: "detected" | "not_found" | "disabled";
    pattern?: string;
    convention?: string;
    confidence?: number;
    marker_count?: number;
    first?: number | null;
    last?: number | null;
    reason?: string;
  };
  ocr_pages: number;
  warnings: string[];
  metadata: Record<string, unknown>;
  media_kind?: string;
  source_illegibility?: number;
  deterministic_checked_at?: string;
  initial_metadata?: {
    title?: string;
    document_author?: string;
    speaker?: string;
    speakers?: string[];
    language?: string;
    language_status?:
      "deterministic" | "llm_proposed" | "human_confirmed" | "confirmed_absent" | "unresolved";
    [key: string]: unknown;
  };
  document_layout?: DocumentLayoutPlan;
  document_layout_revision?: number;
  pages?: Array<{
    pdf_page: number;
    printed_page_label?: string | null;
    printed_page_label_source?: string | null;
    width: number;
    height: number;
    block_ids?: string[];
    extraction_method?: string;
    image_count?: number;
    logical_pages?: Array<{ slot: string; printed_page_label?: string | null }>;
    deterministic_region_type?: string;
    thread_ids?: string[];
  }>;
  source_quality?: {
    valid_for_enrichment?: boolean;
    page_count?: number;
    blocking_page_count?: number;
    warning_page_count?: number;
    image_only_page_count?: number;
    blocking_pages?: number[];
    warning_pages?: number[];
    issues?: Array<{
      page?: number;
      severity?: string;
      codes?: string[];
      characters?: number;
      replacement_characters?: number;
      control_characters?: number;
      extraction_methods?: Record<string, number>;
    }>;
  };
  /** Audio sources only: probed at ingest; absent on assets stored before it was recorded. */
  audio_provenance?: { duration_seconds?: number };
  extraction_noise?: {
    page_count?: number;
    unusable_page_count?: number;
    unusable_page_ratio?: number;
    median_noise?: number | null;
    threshold?: number;
    exceeds_threshold?: boolean;
    pages?: Array<{
      page?: number;
      score?: number;
      unusable?: boolean;
      reasons?: string[];
      effective_dpi?: number | null;
    }>;
  };
}

export interface RecordContextItem {
  record_id: string;
  text: string;
  text_length: number;
  page_start: number | string | null;
  page_end: number | string | null;
  review_disposition?: string | null;
}

/** Neighbouring records' text, in document order (farthest first before, nearest first after). */
export interface RecordContext {
  record_id: string;
  before: RecordContextItem[];
  after: RecordContextItem[];
  truncated: boolean;
}

/** Result of split / merge / create-from-selection: affected records are retired and new ones minted. */
export interface StructuralEditResult {
  /** The new record the reviewer should land on. */
  record: CorpusRecord;
  records: CorpusRecord[];
  retired_record_ids: string[];
  transaction_id: string;
}

export interface WikisourceHit {
  source: "wikisource";
  /** The Wikisource language edition searched (en, fr, …). */
  language?: string;
  title: string;
  page_id: number;
  snippet: string;
  word_count?: number;
  url: string;
}

export interface GutenbergStatus {
  ready: boolean;
  search_ready: boolean;
  catalogue: {
    status: string;
    refreshed_at?: string | null;
    item_count: number;
    error?: string | null;
  };
  archive: {
    status: string;
    bytes_done: number;
    total_bytes?: number | null;
    error?: string | null;
  };
}

export interface DocumentLayoutPlan {
  page_layout: "single" | "two_up";
  reading_order: "left_to_right" | "right_to_left";
  main_text_pdf_start?: number | null;
  main_text_printed_start?: number | null;
  main_text_slot?: "left" | "right" | null;
  bibliography_pdf_start?: number | null;
  thread_mode: "continuous" | "odd_even" | "even_odd" | "left_right" | "right_left";
  thread_a_language?: string | null;
  thread_b_language?: string | null;
  unit_policy?: SourceUnitPolicy;
  layout_regions?: LayoutRegion[];
}

export interface LlmActivity {
  state: "loading_model" | "working" | "unknown";
  task: "manifest" | "segmentation" | "metadata" | "other";
  model: string;
  provider: string;
  seconds: number;
  calls_in_flight: number;
}
export interface DocumentIntelligenceRun {
  version?: number;
  status: "ok" | "skipped" | "unavailable" | "queued" | string;
  profile?: "none" | "general" | "fiction" | "scholarly" | string;
  provider?: string;
  provider_version?: string;
  model?: string;
  capabilities?: string[];
  model_artifacts?: Array<{
    role?: string;
    name?: string;
    sha256?: string;
  }>;
  configuration?: Record<string, unknown>;
  text_sha256?: string;
  current_text_sha256?: string;
  stale?: boolean;
  warnings?: string[];
  entity_clusters?: Array<{
    cluster_id: string;
    canonical: string;
    aliases?: string[];
    entity_type?: string;
  }>;
  entities?: Array<Record<string, unknown>>;
  quotations?: Array<Record<string, unknown>>;
  characters?: Array<Record<string, unknown>>;
  events?: Array<Record<string, unknown>>;
}

export interface SemanticContentGraphFeature {
  label: string;
  count?: number;
  record_ids?: string[];
}

export interface SemanticContentGraphNode {
  id: string;
  type: string;
  label: string;
  aliases?: string[];
  record_ids?: string[];
  mention_count?: number;
  derivation_method?: string;
  character_profile?: {
    actions_as_agent?: SemanticContentGraphFeature[];
    actions_as_patient?: SemanticContentGraphFeature[];
    possessions?: SemanticContentGraphFeature[];
    modifiers?: SemanticContentGraphFeature[];
  };
}

export interface SemanticContentGraphEdge {
  id: string;
  source: string;
  target: string;
  predicate: string;
  relation_kind: "semantic" | "observational" | string;
  derivation_method?: string;
  authority_status?: string;
  record_ids?: string[];
  evidence_refs?: Array<Record<string, unknown>>;
  supporting_fields?: string[];
  observations?: Array<{
    verb?: string;
    token_id?: number;
    record_id?: string;
    [key: string]: unknown;
  }>;
  count?: number;
}

/** A graph node as it appears in a Record map or node walk. */
export interface RecordSemanticMapNode extends SemanticContentGraphNode {
  /** True when the node occurs in (or takes part in a relation of) the mapped Record. */
  local?: boolean;
  record_count?: number;
  /** POS/NER tags for nodes created from the Record term layer. */
  tags?: string[];
}

export interface RecordSemanticMapEdge extends SemanticContentGraphEdge {
  /** True when the mapped Record supports this relation; false when it leads elsewhere. */
  in_record?: boolean;
}

/** An exact span of the current Record text; `layer` names the annotation that produced it. */
export interface RecordSemanticMention {
  start: number;
  end: number;
  text: string;
  layer: "entity" | "quotation" | "ner" | "pos" | string;
  tag?: string;
  mention_type?: string;
  speaker?: string;
  node_id?: string;
}

export interface SemanticNodeRef {
  id: string;
  label: string;
  type: string;
}

export interface RecordSemanticLinkedRecord {
  record_id: string;
  preview: string;
  score: number;
  shared_node_count: number;
  shared_nodes: SemanticNodeRef[];
  shared_relation_ids: string[];
}

export type SemanticLayerStatus = "ok" | "stale" | "missing" | "unavailable" | string;

export interface RecordSemanticMap {
  version: number;
  kind: "record_semantic_map" | string;
  record_id: string;
  record_revision: number;
  record_text_sha256: string;
  layers: {
    document_intelligence: {
      status: SemanticLayerStatus;
      provider?: string | null;
      model?: string | null;
      profile?: string | null;
    };
    terms: { status: SemanticLayerStatus };
  };
  mentions: RecordSemanticMention[];
  nodes: RecordSemanticMapNode[];
  edges: RecordSemanticMapEdge[];
  linked_records: RecordSemanticLinkedRecord[];
  summary: {
    local_nodes: number;
    shown_local_nodes: number;
    neighbor_nodes: number;
    in_record_edges: number;
    outward_edges: number;
    linked_records: number;
  };
  epistemic_note?: string;
}

/** A reviewer's statement that several surfaces name one identity of a kind. */
export interface SemanticAliasSet {
  alias_set_id: string;
  kind: string;
  canonical_label: string;
  aliases: string[];
  reason?: string;
  reviewer?: string;
  created_at: string;
  retired_at?: string | null;
  replaces?: string | null;
  replaced_by?: string;
  /** Set when a reviewer copied this identity from another corpus build. */
  imported_from?: {
    build_id: string;
    alias_set_id: string;
    build_title?: string;
    reviewer?: string | null;
    created_at?: string;
  } | null;
}

/** Another corpus build whose reviewed identities can be imported. */
export interface SemanticAliasSource {
  build_id: string;
  title: string;
  created_at?: string;
  alias_sets: number;
  kinds: string[];
}

export interface SemanticAliasImportResult {
  imported: SemanticAliasSet[];
  skipped: Array<{
    build_id: string;
    alias_set_id: string;
    canonical_label: string;
    reason: "conflict" | "already_imported" | string;
    detail?: string;
  }>;
}

/** An identity kind the build's schema compares, and the fields that use it. */
export interface SemanticAliasKind {
  kind: string;
  mode: string;
  fields: string[];
}

export interface SemanticAliasList {
  items: SemanticAliasSet[];
  kinds: SemanticAliasKind[];
}

export interface SemanticAliasDraft {
  kind: string;
  canonical_label: string;
  aliases: string[];
  reason?: string;
  replaces?: string | null;
}

export interface SemanticNodeNeighborhood {
  version: number;
  kind: "semantic_node_neighborhood" | string;
  node: RecordSemanticMapNode;
  nodes: RecordSemanticMapNode[];
  edges: SemanticContentGraphEdge[];
  total_edges: number;
  records: Array<{ record_id: string; preview: string }>;
  total_records: number;
  epistemic_note?: string;
}

export interface SemanticContentGraph {
  version: number;
  kind: "semantic_content_graph" | string;
  profile?: string;
  nodes: SemanticContentGraphNode[];
  edges: SemanticContentGraphEdge[];
  summary?: {
    nodes?: number;
    edges?: number;
    semantic_edges?: number;
    observational_edges?: number;
    characters?: number;
    persons?: number;
    concepts?: number;
    works?: number;
  };
  epistemic_note?: string;
}

export interface SemanticGraphViewNode {
  id: string;
  type: string;
  label: string;
  aliases?: string[];
  mention_count: number;
  record_count: number;
  degree: number;
}

export interface SemanticGraphViewEdge {
  id: string;
  source: string;
  target: string;
  predicate: string;
  relation_kind: "semantic" | "observational" | string;
  authority_status: string;
  count: number;
}

export interface SemanticGraphViewRelation extends SemanticGraphViewEdge {
  direction: "incoming" | "outgoing";
  other_id: string;
  other_label: string;
  other_type: string;
  record_ids: string[];
  record_count: number;
  supporting_fields: string[];
  derivation_method: string;
  evidence_ref_count: number;
  observed_verbs: string[];
}

export type SemanticRelationKindFilter = "all" | "semantic" | "observational";
export type SemanticIndexSort = "mentions" | "label" | "degree" | "records";

export interface SemanticGraphViewParams {
  q?: string;
  types?: string[];
  relation_kind?: SemanticRelationKindFilter;
  focus?: string;
  node_limit?: number;
  edge_limit?: number;
  min_mentions?: number;
  index_offset?: number;
  index_limit?: number;
  index_sort?: SemanticIndexSort;
}

/** Bounded, ranked slice of the semantic graph; the full projection stays server-side. */
export interface SemanticContentGraphView {
  version: number;
  kind: "semantic_content_graph_view" | string;
  profile?: string;
  summary: NonNullable<SemanticContentGraph["summary"]>;
  epistemic_note?: string;
  facets: {
    types: Array<{ type: string; count: number }>;
    predicates: Array<{ relation_kind: string; predicate: string; count: number }>;
  };
  query: Required<Pick<SemanticGraphViewParams, "relation_kind" | "focus">> & {
    query: string;
    types: string[];
    node_limit: number;
    edge_limit: number;
    min_mentions: number;
  };
  view: {
    nodes: SemanticGraphViewNode[];
    edges: SemanticGraphViewEdge[];
    candidate_nodes: number;
    candidate_edges: number;
    truncated_nodes: boolean;
    truncated_edges: boolean;
  };
  focus: {
    node: SemanticGraphViewNode & {
      derivation_method?: string;
      record_ids?: string[];
      character_profile?: SemanticContentGraphNode["character_profile"] | null;
    };
    relations: SemanticGraphViewRelation[];
    relations_total: number;
  } | null;
  index: {
    items: SemanticGraphViewNode[];
    total: number;
    offset: number;
    limit: number;
    sort: SemanticIndexSort;
  };
}

export interface AutonomousPolicy {
  enabled: boolean;
  passes: number;
  min_confidence: number;
  unresolved: "best_guess" | "leave";
  accept_records: boolean;
  publish: boolean;
}
export interface AutonomousReport {
  records: number;
  accepted: number;
  fields_filled: number;
  decisions?: number;
  left_for_review: number;
  passes_run: number;
  ran_at: string;
  exceptions: { record_id: string; reasons: string[] }[];
  notes: string[];
  policy: AutonomousPolicy;
  published?: boolean;
}
import type { MetadataSchema } from "../metadataSchemas";
export interface CorpusLlmTraceEntry {
  call_id: string;
  schema_name?: string;
  role?: string;
  attempt?: number;
  provider?: string;
  model?: string;
  prompt?: string;
  response_schema?: Record<string, unknown>;
  generation?: Record<string, unknown>;
  max_tokens?: number;
  started_at?: string;
  finished_at?: string;
  status?: "running" | "complete" | "failed" | string;
  raw_response?: string;
  validated_response?: Record<string, unknown>;
  error?: string | null;
}

export interface CorpusBuild {
  /** The metadata schema this build was started with: its own copy, unaffected by later edits to the saved one. */
  schema?: MetadataSchema | null;
  schema_id?: string;
  schema_name?: string;
  linguistic_annotations?: {
    status?: string;
    engine?: string;
    engine_version?: string;
    models?: string[];
    languages?: string[];
    records_total?: number;
    records_annotated?: number;
    records_unavailable?: number;
  };
  document_intelligence?: {
    status?: string;
    profile?: string;
    selected_provider?: string;
    provider?: string;
    provider_version?: string;
    model?: string;
    capabilities?: string[];
    entity_clusters?: number;
    characters?: number;
    entity_mentions?: number;
    quotations?: number;
    events?: number;
    model_artifacts?: Array<{
      role?: string;
      name?: string;
      sha256?: string;
    }>;
    warnings?: string[];
    reason?: string;
    text_sha256?: string;
  };
  semantic_content_graph?: SemanticContentGraph["summary"];
  /** What the last hands-free run settled and left. */
  autonomous_report?: AutonomousReport | null;
  /** A live reading of the oldest model call in flight; not stored with the build. */
  llm_activity?: LlmActivity | null;
  build_id: string;
  asset_id: string;
  source_filename: string;
  source_sha256: string;
  status: string;
  stage: string;
  progress: number;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  record_count: number;
  source_block_count?: number;
  needs_review_count: number;
  accepted_count: number;
  rejected_count?: number;
  source_problem_count?: number;
  review_queue_counts?: {
    all?: number;
    ready?: number;
    preparing?: number;
    issues?: number;
    metadata?: number;
    topology?: number;
    source?: number;
    accepted?: number;
    rejected?: number;
    pending?: number;
  };
  model?: string | null;
  provider?: string | null;
  profile_id: string;
  schema_version?: string;
  metadata_schema_version?: string;
  segmentation_prompt_version?: string;
  metadata_prompt_version?: string;
  document_prompt_version?: string;
  validation?: {
    valid?: boolean;
    source_valid?: boolean;
    metadata_valid?: boolean;
    coverage?: number;
    missing_block_ids?: string[];
    duplicate_block_ids?: string[];
    text_fidelity_errors?: string[];
    source_order_errors?: string[];
    page_mapping_errors?: string[];
    printed_page_label_errors?: string[];
    metadata_evidence_errors?: Array<{ record_id?: string; field?: string; reason?: string }>;
    metadata_schema_errors?: Array<{ record_id?: string; reason?: string }>;
    citation_errors?: string[];
    relationship_errors?: string[];
    human_ownership_errors?: string[];
    record_content_errors?: string[];
    validation_issues?: Array<{
      code?: string;
      record_id?: string;
      field?: string;
      reason?: string;
    }>;
  };
  manifest?: Record<string, unknown>;
  manifest_revision?: number;
  manifest_confirmed_at?: string | null;
  manifest_confirmed_revision?: number | null;
  publication?: {
    publication_id: string;
    filename: string;
    sha256: string;
    record_count: number;
    created_at: string;
    /** Decision provenance, independent from cELF conformance. */
    review_mode?: "reviewed" | "autonomous" | "hybrid" | "unreviewed";
    decision_mode?: "reviewed" | "autonomous" | "hybrid" | "unreviewed";
    celf_conformant?: boolean;
    celf_conformance?: {
      spec_version?: string;
      conformant?: boolean;
      core?: { status?: string; blockers?: Array<Record<string, unknown>> };
      publication?: { status?: string; blockers?: Array<Record<string, unknown>> };
    };
    human_reviewed_record_count?: number;
    autonomous_record_count?: number;
    unreviewed_record_count?: number;
    unreviewed_accepted_field_count?: number;
  } | null;
  publication_status?: "unpublished" | "published";
  provider_profile_history?: Array<{
    at?: string;
    provider_profile_id?: string;
    provider?: string;
    model?: string;
    metadata_completed?: number;
    note?: string;
  }>;
  published_at?: string | null;
  error?: string | null;
  /** Who acknowledged which warning, and when, keyed by warning ID. Acknowledged warnings stay in the provenance. */
  warning_acknowledgements?: Record<
    string,
    { warning: string; acknowledged_by?: string; acknowledged_at?: string }
  >;
  warnings?: string[];
  resumable?: boolean;
  boundary_count?: number;
  boundary_candidate_count?: number;
  boundary_candidates_completed?: number;
  segmentation_degraded?: boolean;
  segmentation_failed_windows?: number;
  segmentation_total_windows?: number;
  segmentation_recovered_windows?: number;
  segmentation_blocked?: boolean;
  retrying_segmentation?: boolean;
  segmentation_unresolved_regions?: Array<{
    after_block_id?: string;
    next_block_id?: string;
    left_block_id?: string;
    right_block_id?: string;
    start_block_id?: string;
    end_block_id?: string;
    reason?: string;
    kind?: string;
    [key: string]: unknown;
  }>;
  segmentation_boundary_reviews?: Array<{
    after_block_id?: string;
    next_block_id?: string;
    reason?: string;
    kind?: string;
    [key: string]: unknown;
  }>;
  boundary_review_count?: number;
  provisional_boundary_count?: number;
  boundary_deterministic_split_count?: number;
  boundary_deterministic_keep_count?: number;
  boundary_llm_adjudication_count?: number;
  boundary_llm_batch_call_count?: number;
  boundary_llm_split_count?: number;
  boundary_llm_keep_count?: number;
  boundary_budget_skipped_count?: number;
  boundary_classifier_failure_count?: number;
  boundary_second_reader_count?: number;
  boundary_second_reader_keep_count?: number;
  boundary_second_reader_move_count?: number;
  boundary_second_reader_uncertain_count?: number;
  boundary_second_reader_failure_count?: number;
  topology_validation?: {
    valid?: boolean;
    issues?: string[];
    findings?: Array<{
      code: string;
      severity: string;
      record_id?: string | null;
      auto_repairable?: boolean;
      params?: Record<string, unknown>;
    }>;
    record_count?: number;
    max_record_chars?: number;
    min_record_chars?: number;
    median_record_chars?: number;
    p10_record_chars?: number;
    p90_record_chars?: number;
    preferred_record_chars?: number;
    record_length_tolerance?: number;
    long_record_chars?: number;
    absolute_record_chars?: number;
    records_in_preferred_range?: number;
    records_over_preferred_range?: number;
    records_over_long_limit?: number;
    micro_record_count?: number;
  };
  topology_quality?: {
    valid?: boolean;
    source_block_count?: number;
    used_source_block_count?: number;
    source_coverage?: number;
    source_order_valid?: boolean;
    source_conservation_valid?: boolean;
    record_count?: number;
    median_record_chars?: number;
    p10_record_chars?: number;
    p90_record_chars?: number;
    max_record_chars?: number;
    records_in_preferred_range?: number;
    records_over_preferred_range?: number;
    records_over_long_limit?: number;
    micro_record_count?: number;
    policy?: Record<string, number>;
  };
  record_sizing_policy?: Record<string, number>;
  size_optimized_boundary_count?: number;
  absolute_safety_boundary_count?: number;
  long_exception_record_count?: number;
  metadata_completed?: number;
  metadata_total?: number;
  metadata_enriched_count?: number;
  metadata_enrichment_total?: number;
  metadata_concurrency?: number;
  metadata_tasks_total?: number;
  metadata_tasks_completed?: number;
  metadata_tasks_failed?: number;
  metadata_tasks_skipped?: number;
  metadata_tasks_running?: number;
  metadata_tasks_queued?: number;
  metadata_started_at?: string | null;
  metadata_last_progress_at?: string | null;
  metadata_settle_requested?: boolean;
  metadata_active_tasks?: Array<{ record_id?: string; task?: string; started_at?: string | null }>;
  metadata_issue_summary?: {
    records_incomplete?: number;
    fields_unresolved?: number;
    by_field?: Record<string, number>;
    by_reason?: Record<string, number>;
    invalid_by_field?: Record<string, number>;
    auto_retry_records?: number;
    human_review_records?: number;
    auto_retry_fields?: number;
    human_review_fields?: number;
    issues?: Array<{
      record_id?: string;
      field?: string;
      issue_type?: string;
      retryable?: boolean;
      status?: string;
      reason?: string;
      method?: string;
      confidence?: number | null;
      current_value?: unknown;
      page_start?: number | string | null;
      page_end?: number | string | null;
    }>;
    records?: Array<{
      record_id?: string;
      fields?: string[];
      issues?: Array<Record<string, unknown>>;
      page_start?: number | string | null;
      page_end?: number | string | null;
    }>;
  };
  metadata_operation?: {
    operation_id?: string;
    kind?: string;
    state?: "queued" | "running" | "completed" | "failed" | string;
    started_at?: string;
    finished_at?: string | null;
    records_total?: number;
    records_processed?: number;
    records_unchanged?: number;
    records_enriched?: number;
    records_reopened?: number;
    records_skipped?: number;
    fields_total?: number;
    fields_resolved?: number;
    fields_remaining?: number;
    provider_profile_id?: string | null;
    provider?: string | null;
    model?: string | null;
    target_fields?: Record<string, string[]>;
    error?: string | null;
    passes_requested?: number;
    passes_completed?: number;
    current_pass?: number;
    current_record_id?: string | null;
    current_task?: string | null;
    active_tasks?: Array<{
      record_id?: string;
      task?: string;
      state?: string;
      started_at?: string;
    }>;
    converged?: boolean;
    records_disputed?: number;
    fields_replaced?: number;
    fields_kept?: number;
    pass_results?: { pass: number; records_processed?: number; fields_added?: number }[];
  };
  trash_quality?: {
    record_count?: number;
    trash_record_count?: number;
    trash_ratio?: number;
    threshold?: number;
    exceeds_threshold?: boolean;
    deterministic?: boolean;
    unusable_page_count?: number;
    unusable_page_ratio?: number;
    median_noise?: number | null;
    noise_unusable_threshold?: number;
  };
  source_quality?: {
    valid_for_enrichment?: boolean;
    page_count?: number;
    blocking_page_count?: number;
    warning_page_count?: number;
    image_only_page_count?: number;
    blocking_pages?: number[];
    warning_pages?: number[];
    issues?: Array<{
      page?: number;
      severity?: string;
      codes?: string[];
      characters?: number;
      replacement_characters?: number;
      control_characters?: number;
      extraction_methods?: Record<string, number>;
    }>;
  };
  pipeline_state?: {
    current?: string;
    stages?: Record<string, { state?: string; [key: string]: unknown }>;
  };
  publication_readiness?: {
    can_publish?: boolean;
    next_action?: string;
    blockers?: Array<{ code?: string; count?: number; fields?: string[] }>;
    required_metadata_fields?: string[];
    required_document_fields?: string[];
    missing_document_fields?: string[];
    records_total?: number;
    records_reviewed?: number;
    records_accepted?: number;
    records_rejected?: number;
    records_pending?: number;
    metadata_records_remaining?: number;
    metadata_fields_unresolved?: number;
    source_valid?: boolean;
    metadata_valid?: boolean;
    published?: boolean;
    no_publishable_records?: boolean;
  };
  build_events?: Array<{ at?: string; stage?: string; status?: string; progress?: number }>;
  request?: Record<string, unknown>;
  llm_metrics?: {
    calls?: number;
    retries?: number;
    structured_output_failures?: number;
    escalations?: number;
    editorial_examples_used?: number;
  };
  llm_contribution?: {
    inherited_fields?: number;
    deterministic_fields?: number;
    llm_fields_usable?: number;
    llm_fields_proposed?: number;
    llm_fields_review?: number;
    human_fields?: number;
    family_calls?: number;
    elapsed_ms?: number;
    useful_fields_per_minute?: number;
    tasks_complete?: number;
    tasks_failed?: number;
    tasks_skipped?: number;
    enrichment_mode?: string;
    semantic_indexing?: boolean;
  };
  llm_family_effectiveness?: Record<
    string,
    {
      calls?: number;
      proposed_fields?: number;
      elapsed_ms?: number;
      human_accepted_fields?: number;
      human_corrected_fields?: number;
      last_updated_at?: string;
      last_human_feedback_at?: string;
    }
  >;
  llm_model_effectiveness?: Record<
    string,
    {
      provider_profile_id?: string | null;
      provider?: string | null;
      model?: string | null;
      calls?: number;
      proposed_fields?: number;
      elapsed_ms?: number;
    }
  >;
  llm_confidence_calibration?: Record<
    string,
    Record<
      string,
      { reviewed?: number; accepted?: number; corrected?: number; acceptance_rate?: number }
    >
  >;
  text_cleanup?: {
    enabled?: boolean;
    rules?: string[];
    records_changed?: number;
    changes?: number;
    removed_lines?: number;
    recurring_line_patterns?: number;
  };
}

export interface CorpusRecord {
  record_id: string;
  text: string;
  text_length: number;
  source_document_id?: string;
  source_unit_ids?: string[];
  page_start?: number | string | null;
  page_end?: number | string | null;
  source_block_ids: string[];
  source_spans: Array<{
    source_unit_id?: string;
    block_id?: string;
    page?: number;
    start?: number;
    end?: number;
    speaker?: string;
    locator_kind?: string;
    bbox?: number[];
    extraction_method?: string;
  }>;
  metadata_evidence?: Record<
    string,
    {
      block_ids?: string[];
      /** Spans cited from other records of the same source. */
      external_block_ids?: string[];
      source_kind?: string;
      confidence?: number;
      reason?: string;
      reviewed_by?: string;
      reviewed_at?: string;
    }
  >;
  metadata_guidance_matches?: Record<string, Array<{ term: string; occurrences: number }>>;
  metadata_field_status?: Record<
    string,
    {
      status?:
        "deterministic" | "model_inferred" | "human_confirmed" | "unresolved" | "invalid" | string;
      method?: string;
      confidence?: number | null;
      reason?: string;
      reason_code?: string;
      proposed_value?: unknown;
      auto_populated?: boolean;
      autofilled?: boolean;
      verification_status?: "pending_review" | "auto_resolved" | "human_confirmed" | string;
      value_source?: "llm" | "deterministic" | "human" | string;
      llm_requested?: boolean;
      llm_value_returned?: boolean;
      llm_assessed?: boolean;
      llm_checked?: boolean;
      audit_sample?: boolean;
      self_reported_confidence?: number;
      model?: string;
    }
  >;
  metadata_incomplete_fields?: string[];
  metadata_review_fields?: string[];
  metadata_reviewed_at?: string;
  metadata_decisions?: Array<{ field?: string; value?: unknown; at?: string; source?: string }>;
  metadata_enrichment_history?: Array<{
    run_id?: string;
    pass?: number;
    at?: string;
    state?: string;
    outcome?: string;
    model?: string;
    added_fields?: string[];
    replaced?: Array<{ field?: string; previous?: unknown; value?: unknown }>;
    disputes?: Array<Record<string, unknown>>;
    informational?: Array<{
      kind?: string;
      field?: string;
      authoritative_value?: unknown;
      proposed_value?: unknown;
      confidence?: number;
      reason?: string;
      run_id?: string;
      pass?: number;
      model?: string | null;
      at?: string;
    }>;
  }>;
  activity?: {
    human_view_count?: number;
    human_review_count?: number;
    llm_review_count?: number;
    enrichment_pass_count?: number;
    last_human_viewed_at?: string;
    last_human_reviewed_at?: string;
    last_llm_reviewed_at?: string;
    last_enrichment_provider?: string;
    last_enrichment_model?: string;
  };
  human_view_count?: number;
  metadata_stage_status?: Record<string, string>;
  metadata_execution_ledger?: Record<
    string,
    {
      state?: string;
      started_at?: string;
      finished_at?: string | null;
      elapsed_ms?: number;
      error?: string | null;
    }
  >;
  metadata_enrichment_state?: "queued" | "running" | "complete" | "failed" | string;
  metadata_enrichment_finished?: boolean;
  human_touched_fields?: string[];
  human_touched_at?: string;
  human_touched_revision?: number;
  metadata_complete?: boolean;
  metadata_needs_attention?: boolean;
  metadata_attention_reasons?: string[];
  source_quality_issues?: Array<{
    code?: string;
    severity?: string;
    pages?: number[];
    message?: string;
    micro_line_ratio?: number;
    page_findings?: Array<Record<string, unknown>>;
    noise?: number;
  }>;
  text_noise?: {
    score?: number;
    deterministic_score?: number;
    raster_score?: number | null;
    llm_score?: number | null;
    threshold?: number;
    unusable?: boolean;
    reasons?: string[];
    method?: string;
  };
  resolved_source_quality_issues?: Array<Record<string, unknown>>;
  source_extracted_text?: string;
  text_review_status?: "human_corrected" | string;
  text_touchup_proposal?: {
    proposal_id?: string;
    run_id?: string;
    status?: string;
    source_text?: string;
    proposed_text?: string;
    changes?: string[];
    warnings?: string[];
    provider?: string;
    model?: string;
    created_at?: string;
    no_change?: boolean;
    updated_at?: string;
  };
  text_reviewed_at?: string;
  text_revision_history?: Array<{
    at?: string;
    source?: string;
    previous_sha256?: string;
    text_sha256?: string;
    previous_length?: number;
    text_length?: number;
    diff?: string;
    resolved_source_issues?: boolean;
  }>;
  review_events?: Array<{
    at?: string;
    event?: string;
    transaction_id?: string;
    direction?: string;
    source_record_id?: string;
    [key: string]: unknown;
  }>;
  boundary_quality_issues?: Array<{
    code?: string;
    edge?: string;
    reason?: string;
    decision?: string;
    confidence?: number;
    suggested_after_block_id?: string | null;
  }>;
  boundary_llm_before?: {
    boundary_id?: string;
    decision?: "keep" | "move_earlier" | "move_later" | "uncertain";
    suggested_after_block_id?: string | null;
    current_after_block_id?: string | null;
    confidence?: number;
    signals?: string[];
    reason?: string;
    source?: string;
    editorial_examples_used?: number;
    adjudicated_at?: string;
  };
  boundary_llm_after?: {
    boundary_id?: string;
    decision?: "keep" | "move_earlier" | "move_later" | "uncertain";
    suggested_after_block_id?: string | null;
    current_after_block_id?: string | null;
    confidence?: number;
    signals?: string[];
    reason?: string;
    source?: string;
    editorial_examples_used?: number;
    adjudicated_at?: string;
  };
  needs_review?: boolean;
  review_reason?: string;
  accepted?: boolean;
  rejected?: boolean;
  review_disposition?: "pending" | "accepted" | "rejected";
  review_state?: "ready" | "metadata" | "topology" | "source" | "accepted" | "rejected" | string;
  review_issue_codes?: string[];
  acceptance_blocking_fields?: string[];
  can_accept?: boolean;
  record_revision?: number;
  topology_index?: number;
  topology_count?: number;
  pdf_pages?: number[];
  [key: string]: unknown;
}

export interface SourceBlock {
  start?: number;
  end?: number;
  locator_kind?: string;
  block_id: string;
  page: number;
  bbox: number[];
  type: string;
  text: string;
  extraction_method: string;
  confidence: number;
  speaker?: string;
}

export interface GutenbergHit {
  etext_id: number;
  title: string;
  author: string;
  language: string;
}

export interface EnrichmentModelMetrics {
  proposals: number;
  reviews: number;
  autofilled: number;
  acceptance_rate: number | null;
  /** Accepted reviews split by whether the reviewer restated the value (J.P. → J. P.). */
  accepted_exact?: number;
  accepted_equivalent?: number;
  accepted_equivalent_rate?: number | null;
  /** Reviewer values saved when equivalence could not be decided; in no denominator. */
  unresolved_reviews?: number;
  brier_score: number | null;
  correction_rate: number | null;
  rejection_rate: number | null;
  autofill_precision: number | null;
  stability: number | null;
  touched_share: number | null;
  grounded_rate: number | null;
  ms_per_accepted_field: number | null;
  precision_at_threshold: {
    threshold: number;
    reviews: number;
    precision: number | null;
    coverage: number | null;
  }[];
  learning_curve: { reviews_before: number; acceptance: number | null }[];
  acceptance_ci: Interval;
  substantive_error_rate: Interval;
  autofill_precision_ci: Interval;
  spot_checks_still_needed: number;
  correction_severity: Record<string, number>;
  supported_rate: number | null;
  supported_checked: number;
  repeat_rate: number | null;
  proposals_after_a_rejection: number;
  review_seconds_per_decision: number | null;
  seconds_to_first_useful_value: number | null;
  autofill_suspensions: number;
  autofill_resumptions: number;
}

export interface Interval {
  rate: number | null;
  low: number | null;
  high: number | null;
  n: number;
}

export interface EnrichmentMetrics {
  self_consistency?: Interval;
  inter_annotator?: Interval & { kappa: number | null };
  models: Record<string, EnrichmentModelMetrics>;
  inter_model_agreement: { compared: number; agreement: number | null };
  unresolved_remaining: number | null;
  runs: string[];
  concurrency: { limit: number; working: number };
}

/** Evidence a reviewer supplies beyond selected text in the record itself. */
export interface HumanEvidenceSource {
  /** "reviewer_knowledge": the reviewer's own knowledge is the source; no span is cited. */
  source?: "reviewer_knowledge";
  note?: string;
  /** Spans from elsewhere in the same source (another record). */
  externalBlockIds?: string[];
}

// --- Corpus Capture and the Sources workspace ----------------------------------------------------

export type SourceProviderId = "gutenberg" | "wikisource";
export type ContributionRole =
  "author" | "coauthor" | "translator" | "editor" | "contributor" | "about_author" | "unknown";
export type WorkRelationship = "original_language_edition" | "translation" | "edition" | "unknown";
export type IdentityConfidence = "exact" | "probable" | "needs_review";
export type CaptureStatus =
  | "draft"
  | "discovering"
  | "awaiting_review"
  | "acquiring"
  | "partial"
  | "complete"
  | "cancelled"
  | "interrupted"
  | "failed";
export type CandidateAcquisitionStatus =
  "pending" | "fetching" | "acquired" | "registered" | "failed" | "cancelled";
export type SourceBuildStatus = "not_built" | "building" | "built" | "failed";

/** A classified provider/capture failure, as the API reports it in `detail`. */
export interface CaptureErrorInfo {
  code: string;
  message: string;
}

export interface WikisourceProject {
  code: string;
  name: string;
}
export interface GutenbergProviderInfo {
  provider: "gutenberg";
  catalogue_ready: boolean;
  catalogue_refreshed_at?: string | null;
  local_collection_ready: boolean;
}
export interface WikisourceProviderInfo {
  provider: "wikisource";
  projects: WikisourceProject[];
  /** False when Wikimedia's project list was unreachable and a bounded fallback is shown. */
  projects_authoritative: boolean;
}
export type SourceProviderInfo = GutenbergProviderInfo | WikisourceProviderInfo;

export interface AuthorCandidate {
  wikidata_qid: string;
  label: string;
  description: string;
  aliases: string[];
  birth_year: number | null;
  death_year: number | null;
  wikisource_sitelinks: Record<string, string>;
  /** Authoritative work-level original languages only; usually empty until known. */
  original_languages?: string[];
  /** Ordered language signals from Wikidata and the author's source projects. */
  languages?: string[];
}

export interface CaptureOptions {
  providers: SourceProviderId[];
  roles: Exclude<ContributionRole, "unknown">[];
  include_translations: boolean;
  include_originals?: boolean;
  /** null = every available language. */
  languages: string[] | null;
}

export interface CaptureAuthor {
  identity_id?: string;
  canonical_name: string;
  wikidata_qid: string | null;
  aliases?: string[];
  description?: string;
  birth_year: number | null;
  death_year: number | null;
  original_languages?: string[];
  languages?: string[];
}

export interface CaptureSummary {
  candidates: number;
  work_groups: number;
  languages: Record<string, number>;
  providers: Record<string, number>;
  projects: Record<string, number>;
  roles: Record<string, number>;
  translations: number;
  possible_duplicates: number;
  needs_review: number;
  selected: number;
  acquisition: Record<string, number>;
}

export interface ProviderSnapshot {
  provider: SourceProviderId;
  projects_searched: string[];
  identities_used: string[];
  result_count: number;
  pagination_complete: boolean;
  catalog_version?: string | null;
  catalog_refreshed_at?: string | null;
  endpoint?: string | null;
  warnings?: string[] | null;
  errors?: Array<CaptureErrorInfo & { project?: string }> | null;
  searched_at?: string;
}

export interface CaptureRefreshDiff {
  new: number;
  changed: number;
  unchanged: number;
  missing: number;
  new_ids: string[];
  changed_ids: string[];
  missing_ids: string[];
}

/** The durable job driving a capture, while one runs. */
export interface CaptureJob {
  id: string;
  type: "corpus_capture";
  mode: "discover" | "acquire" | "retry" | "refresh";
  status: string;
  stage: string;
  stage_detail: string;
  completed: number;
  total: number;
}

export interface CorpusCapture {
  capture_id: string;
  author: CaptureAuthor;
  options: CaptureOptions;
  status: CaptureStatus;
  phase: string;
  created_at: string;
  updated_at?: string;
  discovery_started_at?: string | null;
  discovery_completed_at: string | null;
  last_refreshed_at: string | null;
  provider_snapshots: ProviderSnapshot[];
  summary: CaptureSummary;
  progress: { done?: number; total?: number; current?: string; project?: string };
  warnings: string[];
  errors: Array<CaptureErrorInfo & { provider?: string }>;
  last_refresh_diff: CaptureRefreshDiff | null;
  discovery_contract_version: string;
  active_job: CaptureJob | null;
}

/** A capture row in the captures list (no snapshots or progress). */
export type CorpusCaptureListItem = Pick<
  CorpusCapture,
  | "capture_id"
  | "status"
  | "phase"
  | "created_at"
  | "discovery_completed_at"
  | "last_refreshed_at"
  | "summary"
> & { author: CaptureAuthor };

export interface CaptureCandidate {
  candidate_id: string;
  provider: SourceProviderId;
  provider_item_id: string;
  title: string;
  document_author: string;
  contribution_role: ContributionRole;
  document_languages: string[];
  original_language: string | null;
  source_project_language: string | null;
  translators: string[];
  editors: string[];
  publication_year: number | null;
  edition: string | null;
  source_uri: string;
  catalog_uri: string | null;
  wikidata_work_id: string | null;
  wikidata_edition_id: string | null;
  canonical_work_id: string;
  relationship_to_work: WorkRelationship;
  reconciliation_status: "exact_identity" | "deterministic_match" | "possible_match" | "separate";
  possible_duplicates: string[] | null;
  identity_confidence: IdentityConfidence;
  selection_status: "selected" | "excluded";
  selection_reason: string;
  acquisition_status: CandidateAcquisitionStatus;
  source_document_id: string | null;
  digital_duplicate_of: string | null;
  error: CaptureErrorInfo | null;
  upstream_status: "present" | "missing" | null;
  metadata_changed_fields: string[] | null;
  discovery_method: string;
  discovery_evidence: Record<string, unknown>;
  discovered_at: string | null;
  acquired_at: string | null;
  rights_status: string | null;
  rights_source: string | null;
}

export interface CaptureCandidatePage {
  items: CaptureCandidate[];
  total: number;
  offset: number;
  limit: number;
}

/** A compact Sources row: identity, language and status only — never text or blocks. */
export interface SourceRow {
  source_document_id: string;
  title: string;
  filename: string;
  provider: string;
  provider_item_id: string | null;
  document_author: string | null;
  document_languages: string[];
  original_language: string | null;
  source_project_language: string | null;
  canonical_work_id: string | null;
  relationship_to_work: WorkRelationship | null;
  contribution_role: ContributionRole | null;
  edition: string | null;
  translator: string | null;
  media_kind: string;
  acquisition_status: string;
  source_hash_short: string | null;
  created_at: string | null;
  derived_from_asset_id: string | null;
  block_count: number | null;
  capture_ids: string[];
  build_status: SourceBuildStatus;
  build_count: number;
  latest_build_id: string | null;
}

export type SourceFacetName =
  | "provider"
  | "document_language"
  | "original_language"
  | "capture_id"
  | "build_status"
  | "relationship"
  | "role"
  | "media_kind";
export type SourceSort = "title" | "added" | "provider" | "language" | "author";

export interface SourceListQuery {
  q?: string;
  provider?: string[];
  document_language?: string[];
  original_language?: string[];
  capture_id?: string[];
  build_status?: string[];
  relationship?: string[];
  role?: string[];
  ids?: string[];
  sort?: SourceSort;
  order?: "asc" | "desc";
  offset?: number;
  limit?: number;
}

export interface SourceListResponse {
  items: SourceRow[];
  total: number;
  offset: number;
  limit: number;
  all_total: number;
  facets: Record<SourceFacetName, Record<string, number>>;
}

export interface SourceCaptureLink {
  capture_id: string;
  candidate_id: string;
  provider: string;
  provider_item_id: string;
  discovery_method: string;
  discovered_at: string | null;
  acquired_at: string;
  author_name: string | null;
}

export interface SourceDetail {
  asset_id: string;
  sha256: string;
  filename: string;
  created_at: string;
  media_type?: string | null;
  media_kind?: string | null;
  content_suffix?: string | null;
  source_url?: string | null;
  page_count?: number | null;
  block_count?: number | null;
  ocr_pages?: number | null;
  extraction_provenance?: Record<string, unknown> | null;
  catalog_metadata: Record<string, unknown>;
  initial_metadata: Record<string, string | number | null>;
  derived_from_asset_id?: string | null;
  captures: SourceCaptureLink[];
  builds: Array<{
    build_id: string;
    status: string;
    created_at: string | null;
    record_count: number | null;
  }>;
}

export interface SourceBulkDeleteResult {
  items: Array<{
    source_document_id: string;
    deleted: boolean;
    removed?: string[];
    reason?: "in_use" | "not_found";
    message?: string;
  }>;
}
