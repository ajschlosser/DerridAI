/* Copyright 2026 Aaron John Schlosser, PhD. */

export type PipelineStageFamily =
  | "query_transform"
  | "candidate_generation"
  | "filter"
  | "normalization"
  | "fusion"
  | "rerank"
  | "support_validation"
  | "diversity"
  | "selection"
  | "context_pack"
  | "llm"
  | "evaluation";

/** What a stage may establish about evidence, support or provenance (server vocabulary). */
export type PipelineScholarlyEffect =
  | "none"
  | "advisory"
  | "scope_constraint"
  | "eligibility_gate"
  | "provenance_gate"
  | "transformation"
  | "generation"
  | "evaluation";

export type PipelineWorkflowCategory =
  | "research"
  | "evidence"
  | "search"
  | "metadata"
  | "memory"
  | "corpus";

/** How a registered strategy fits one purpose's runtime adapter. */
export type PipelineStrategyFit = "supported" | "inspect_only" | "output_contract";

export type PipelineVocabularyTerm = {
  id: string;
  label: string;
  description: string;
  label_key: string;
  description_key: string;
};

export type PipelineWorkflowVocabulary = {
  categories: PipelineVocabularyTerm[];
  guarantees: PipelineVocabularyTerm[];
  phases: PipelineVocabularyTerm[];
  scholarly_effects: PipelineVocabularyTerm[];
  effect_notes: PipelineVocabularyTerm[];
};

/** Server-owned contract for what a whole pipeline is for. */
export type PipelinePurpose = {
  purpose_id: string;
  category: PipelineWorkflowCategory;
  label: string;
  description: string;
  consuming_feature: string;
  consumer: string;
  input_semantics: string;
  output_semantics: string;
  authority_semantics: string;
  output_type: string;
  assignment_scope: string;
  override_allowed: boolean;
  required_guarantees: string[];
  label_key: string;
  description_key: string;
  consumer_key: string;
  input_key: string;
  output_key: string;
  authority_key: string;
  strategy_fit: Record<string, PipelineStrategyFit>;
};

export type PipelineStrategy = {
  strategy_id: string;
  version: number;
  family: PipelineStageFamily;
  scholarly_effect: PipelineScholarlyEffect;
  phase: string;
  effect_note: string;
  label: string;
  label_key?: string;
  description: string;
  description_key?: string;
  input_type: string;
  output_type: string;
  deterministic: boolean;
  invokes_llm: boolean;
  capabilities: string[];
  config_schema: Record<string, unknown>;
};

export type PipelineStage = {
  id: string;
  strategy: string;
  enabled: boolean;
  config: Record<string, unknown>;
  next: string[];
  on_empty?: string | null;
  on_unavailable?: string | null;
  on_timeout?: string | null;
  on_error?: string | null;
};

export type PipelineValidationIssue = {
  level: "error" | "warning";
  code: string;
  message: string;
  stage_id?: string | null;
};

export type PipelineValidation = {
  valid: boolean;
  issues: PipelineValidationIssue[];
};

export type PipelineRuntimeSupport = {
  supported: boolean;
  adapter?: string | null;
  reason?: string | null;
  /** Evidence recovery only: whether every path keeps the direct-support gate. */
  celf_compliant?: boolean | null;
};

export type PipelineDefinition = {
  pipeline_id: string;
  version: number;
  name: string;
  purpose: string;
  status: "draft" | "active" | "disabled";
  entry_stage_ids: string[];
  stages: PipelineStage[];
  built_in?: boolean;
  derived_from?: string | null;
  notes?: string | null;
  created_at?: string | null;
  created_by?: string | null;
  validation?: PipelineValidation;
  runtime_support?: PipelineRuntimeSupport;
};

export type PipelineAssignment = {
  feature: string;
  pipeline_id: string;
  pipeline_version: number;
  scope: string;
  scope_id?: string | null;
  override_allowed: boolean;
  source: string;
};

export type PipelineStageTrace = {
  stage_id: string;
  strategy_id: string;
  strategy_version: number;
  status: string;
  elapsed_ms?: number | null;
  input_count?: number | null;
  output_count?: number | null;
  parameters: Record<string, unknown>;
  provider?: string | null;
  model?: string | null;
  collection?: string | null;
  fallback_reason?: string | null;
  warnings?: string[];
  score_summary?: Record<string, unknown>;
};

export type PipelineRunTrace = {
  run_id: string;
  feature: string;
  pipeline_id: string;
  pipeline_version: number;
  resolved_pipeline: Record<string, unknown>;
  resolved_hash: string;
  owner?: string | null;
  status: string;
  started_at: string;
  finished_at?: string | null;
  total_elapsed_ms?: number | null;
  warnings?: string[];
  stages: PipelineStageTrace[];
};

export type PipelineCatalog = {
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  strategies: PipelineStrategy[];
  pipelines: PipelineDefinition[];
  assignments: PipelineAssignment[];
};

export type ResearchPipelineOptions = {
  assignment: PipelineAssignment;
  override_allowed: boolean;
  pipelines: Array<PipelineDefinition & { assigned?: boolean }>;
  strategies: PipelineStrategy[];
};

export type PipelineValidationResponse = {
  validation: PipelineValidation;
  runtime_supported: boolean;
  runtime_error?: string | null;
};

export type PipelineFeatureMetrics = {
  feature: string;
  run_count: number;
  failed_count: number;
  fallback_run_count: number;
  warning_run_count: number;
  average_elapsed_ms?: number | null;
  p95_elapsed_ms?: number | null;
};

export type PipelineWorkflowMetrics = {
  /** A workflow category, or "unclassified" for features no purpose consumes. */
  category: string;
  features: string[];
  run_count: number;
  failed_count: number;
  fallback_run_count: number;
  warning_run_count: number;
  average_elapsed_ms?: number | null;
  p95_elapsed_ms?: number | null;
};

export type PipelineStrategyMetrics = {
  strategy_id: string;
  stage_ids: string[];
  executions: number;
  fallback_count: number;
  warning_count: number;
  model_call_count: number;
  issue_count: number;
  status_counts: Record<string, number>;
  average_elapsed_ms?: number | null;
  p95_elapsed_ms?: number | null;
  average_input_count?: number | null;
  average_output_count?: number | null;
};

export type PipelineOperationalMetrics = {
  sampled_run_count: number;
  status_counts: Record<string, number>;
  fallback_run_count: number;
  warning_run_count: number;
  average_run_elapsed_ms?: number | null;
  p95_run_elapsed_ms?: number | null;
  workflows: PipelineWorkflowMetrics[];
  features: PipelineFeatureMetrics[];
  strategies: PipelineStrategyMetrics[];
  sample_limit: number;
  feature_filter?: string | null;
  category_filter?: string | null;
  owner_filter?: string | null;
};

export type ResearchPipelineComparisonEvidence = {
  record_id: string;
  rank: number;
  work: string;
  citation: string;
  collection?: string | null;
  distance?: number | null;
  rrf_score?: number | null;
  rerank_score?: number | null;
  retrieval_hits: Array<Record<string, unknown>>;
};

export type ResearchPipelineScoreSummary = {
  count: number;
  minimum?: number | null;
  maximum?: number | null;
  mean?: number | null;
};

export type ResearchPipelineCandidatePhase = {
  count: number;
  record_ids: string[];
  scores: {
    relevance: ResearchPipelineScoreSummary;
    rrf_score: ResearchPipelineScoreSummary;
    rerank_score: ResearchPipelineScoreSummary;
  };
};

export type ResearchPipelineOverlap = {
  shared_record_ids: string[];
  left_only_record_ids: string[];
  right_only_record_ids: string[];
  shared_count: number;
  union_count: number;
  jaccard_overlap: number;
};

export type ResearchPipelineComparisonSide = {
  pipeline: {
    pipeline_id?: string | null;
    pipeline_version?: number | null;
    pipeline_hash?: string | null;
    name?: string | null;
    purpose?: string | null;
  };
  elapsed_seconds?: number | null;
  warnings: string[];
  retrieval: Record<string, unknown>;
  candidate_retention: string;
  candidates: {
    pre_rerank: ResearchPipelineCandidatePhase;
    post_rerank: ResearchPipelineCandidatePhase;
    post_selection: ResearchPipelineCandidatePhase;
  };
  context_characters?: number | null;
  resource_use: {
    query_transform_model_calls: number;
    cross_encoder_calls: number;
  };
  evidence: ResearchPipelineComparisonEvidence[];
  stages: Array<{
    name: string;
    seconds?: number | null;
    detail: Record<string, unknown>;
  }>;
};

export type ResearchPipelineComparisonResult = {
  non_persistent: boolean;
  left: ResearchPipelineComparisonSide;
  right: ResearchPipelineComparisonSide;
  comparison: ResearchPipelineOverlap & {
    candidate_overlap: ResearchPipelineOverlap;
    post_rerank_overlap: ResearchPipelineOverlap;
    elapsed_seconds_delta?: number | null;
    context_characters_delta?: number | null;
    rank_changes: Array<{
      record_id: string;
      left_rank: number;
      right_rank: number;
      rank_delta: number;
    }>;
  };
};

export type ResearchPipelineComparisonRequest = {
  request: {
    prompt: string;
    source_collection: string;
    query_decomposition?: boolean;
  };
  left: { pipeline_id: string; version: number };
  right: { pipeline_id: string; version: number };
};

export type ResearchPipelineBenchmarkCollectionSnapshot = {
  name: string;
  storage_name?: string | null;
  count: number;
  manifest_version?: number | null;
  embedding_provider?: string | null;
  embedding_model?: string | null;
  embedding_dimension?: number | null;
  embedding_revision?: string | null;
  distance_metric?: string | null;
  retrieval_mode?: string | null;
  status?: string | null;
  build_id?: string | null;
  build_created_at?: string | null;
  last_synced_at?: string | null;
  source_kind?: string | null;
  source_label?: string | null;
  source_record_count?: number | null;
  source_snapshot_hash?: string | null;
  app_version?: string | null;
};

export type ResearchPipelineBenchmarkCorpusSnapshot = {
  fingerprint: string;
  collections: ResearchPipelineBenchmarkCollectionSnapshot[];
  limitations: string[];
};

export type ResearchPipelineBenchmarkCaseCreate = {
  case_id: string;
  version: number;
  prompt: string;
  instructions?: string | null;
  source_collection: string;
  locales?: Array<"en" | "fr">;
  search_types?: Array<"similarity" | "lexical" | "mmr">;
  k?: number;
  fetch_k?: number;
  lambda_mult?: number;
  rrf_k?: number;
  rerank_top_n?: number;
  reranker?: "cross_encoder" | "lexical" | "none";
  cross_encoder_model?: string;
  query_decomposition?: false;
  evidence_record_char_limit?: number;
  evidence_total_char_limit?: number;
  notes?: string | null;
};

export type ResearchPipelineBenchmarkCase = ResearchPipelineBenchmarkCaseCreate & {
  corpus_snapshot: ResearchPipelineBenchmarkCorpusSnapshot;
  created_at: string;
  created_by?: string | null;
};

export type ResearchPipelineBenchmarkRequest = {
  case_id: string;
  case_version: number;
  left: { pipeline_id: string; version: number };
  right: { pipeline_id: string; version: number };
};

export type ResearchPipelineBenchmarkRun = {
  benchmark_run_id: string;
  case_id: string;
  case_version: number;
  mode: "retrieval_only";
  created_at: string;
  created_by?: string | null;
  case_snapshot: ResearchPipelineBenchmarkCase;
  fixed_input: {
    prompt: string;
    instructions?: string | null;
    source_collection: string;
  };
  corpus: ResearchPipelineBenchmarkCorpusSnapshot;
  retrieval_config: Record<string, unknown>;
  model_identity: Record<string, unknown>;
  left_pipeline: ResearchPipelineComparisonSide["pipeline"] & {
    resolved_pipeline?: Record<string, unknown> | null;
  };
  right_pipeline: ResearchPipelineComparisonSide["pipeline"] & {
    resolved_pipeline?: Record<string, unknown> | null;
  };
  comparison: ResearchPipelineComparisonResult;
  reproducibility_warnings: string[];
};
