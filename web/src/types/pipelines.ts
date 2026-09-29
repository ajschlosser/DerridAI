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

export type PipelineStrategy = {
  strategy_id: string;
  version: number;
  family: PipelineStageFamily;
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
  features: PipelineFeatureMetrics[];
  strategies: PipelineStrategyMetrics[];
  sample_limit: number;
  feature_filter?: string | null;
  owner_filter?: string | null;
};
