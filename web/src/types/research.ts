/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import type {
  PipelineAssignment,
  PipelineConfigOverrideSet,
  PipelineDefinition,
  PipelineRunTrace,
  PipelineStrategy,
} from "./pipelines";

export type ResearchStore = {
  name: string;
  count: number;
  collection_role?: string;
  embedding_model?: string;
  filter_fields?: string[];
  schema_id?: string;
};

export type ResearchProfile = {
  id: string;
  name?: string;
  type?: "ollama" | "openai";
  model?: string;
  model_mode?: string;
  model_kind?: string;
  max_concurrent_requests?: number;
  num_ctx?: number | string | null;
  num_predict?: number | string | null;
  think?: boolean | string | null;
  temperature?: number | string | null;
  top_k?: number | string | null;
  top_p?: number | string | null;
  min_p?: number | string | null;
  repeat_penalty?: number | string | null;
  seed?: number | string | null;
  mirostat?: number | string | null;
  mirostat_eta?: number | string | null;
  mirostat_tau?: number | string | null;
  keep_alive?: string | null;
  extra_options?: string | Record<string, unknown> | null;
};

export type ResearchFieldAssertionSummary = {
  assertion_id?: string;
  field_id: string;
  field_name: string;
  value: unknown;
  derivation_method?: string;
  evaluation_status?: string;
  authority_status?: string;
  value_status?: string;
  confidence?: number | null;
};

export type ResearchEvidenceSelection = {
  key: string;
  kind?: string;
  collection?: string | null;
  chroma_id?: string | null;
  record_id?: string;
  work?: string;
  page_start?: string | number | null;
  page_end?: string | number | null;
  speaker?: string | null;
  position_holder?: string | null;
  stance?: string | null;
  discourse_role?: string | null;
  target?: string | null;
  proposition_status?: string | null;
  metadata?: Record<string, unknown>;
  assertions?: ResearchFieldAssertionSummary[];
  inline_citation?: string | null;
  text_preview?: string;
  label?: string;
};

export type ResearchResultEvidence = {
  evidence_id?: string;
  inline_citation?: string;
  full_citation?: string;
  collection?: string;
  rerank_score?: number | null;
  record?: Record<string, unknown>;
};

export type ResearchClaimValidationStatus = "unvalidated" | "validated" | "rejected" | "unresolved";

export type ResearchGeneratedClaim = {
  claim_id: string;
  run_id?: string | null;
  response_record_id?: string | null;
  owner?: string | null;
  claim_text: string;
  answer_start?: number | null;
  answer_end?: number | null;
  validation_status?: ResearchClaimValidationStatus;
  validated_by?: string | null;
  validated_at?: string | null;
  created_at?: string | null;
};

export type ResearchClaimSupportBinding = {
  support_binding_id: string;
  claim_id: string;
  owner?: string | null;
  record_id: string;
  record_revision?: number | null;
  source_document_id?: string | null;
  relation?: string | null;
  citation?: {
    inline?: string | null;
    full?: string | null;
    evidence_marker?: string | null;
  } | null;
  validation_status?: "unvalidated" | "validated" | "stale" | "rejected" | "unresolved";
  created_at?: string | null;
};

export type ResearchClaimProvenance = {
  claims: ResearchGeneratedClaim[];
  support_bindings: ResearchClaimSupportBinding[];
};

export type ResearchResult = {
  prompt?: string;
  answer?: string;
  raw_answer?: string;
  provider?: string;
  model?: string;
  elapsed_seconds?: number;
  evidence?: ResearchResultEvidence[];
  stages?: Array<{ name?: string; seconds?: number; detail?: unknown }>;
  warnings?: string[];
  collections?: string[];
  query_metadata?: Record<string, unknown>;
  retrieval?: Record<string, unknown>;
  response_cache?: { record_id?: string } | null;
  auto_grade?: Record<string, unknown> | null;
  auto_grade_provider?: string;
  auto_grade_model?: string;
  rag_request?: Record<string, unknown>;
  claim_provenance?: ResearchClaimProvenance | null;
  pipeline?: {
    pipeline_id?: string;
    pipeline_version?: number;
    pipeline_hash?: string;
    baseline_pipeline_hash?: string;
    config_resolution?: Record<string, unknown>;
    name?: string;
    purpose?: string;
    resolved_pipeline?: Record<string, unknown>;
  } | null;
  pipeline_trace?: PipelineRunTrace | null;
};

export type ResearchJob = {
  id: string;
  type?: string;
  status: string;
  stage?: string;
  stage_detail?: string;
  prompt?: string;
  provider?: string;
  provider_profile_id?: string | null;
  model?: string;
  source_collection?: string;
  owner?: string;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at?: string | null;
  completed?: number;
  total?: number;
  cancel_requested?: boolean;
  fatal_error?: string | null;
  request?: Record<string, unknown> | null;
  result?: ResearchResult | null;
  events?: Array<Record<string, unknown>>;
};

export type ResearchPromptMetadataPolicy = {
  evidence: string[];
  context: string[];
  record: string[];
};

export type ResearchConfig = {
  /** Exact pipeline version to replay; absent means use the current system assignment. */
  pipeline_id?: string;
  pipeline_version?: number | null;
  /** Settings-level stage configuration overrides, keyed by pipeline ID@version. */
  pipeline_config_overrides?: Record<string, PipelineConfigOverrideSet>;
  source_collection: string;
  locales: string[];
  search_types: string[];
  k: number;
  fetch_k: number;
  automatic_sizing: boolean;
  lambda_mult: number;
  rrf_k: number;
  rerank_top_n: number;
  reranker: string;
  cross_encoder_model: string;
  query_decomposition: boolean;
  query_decomposition_num_predict: number;
  response_language: string;
  evidence_record_char_limit: number;
  evidence_total_char_limit: number;
  bind_citations: boolean;
  include_works_cited: boolean;
  prompt_metadata: ResearchPromptMetadataPolicy;
  auto_grade: boolean;
  auto_grade_provider_profile_id: string;
  provider_profile_id: string;
  skip_retrieval: boolean;
  use_prior_response_memory: boolean;
  use_prior_claim_memory: boolean;
  memory_profile_id: string;
  prompt: string;
  instructions: string;
  history?: Array<Record<string, unknown>>;
};

export type ResearchWorkspaceSnapshot = {
  config: ResearchConfig;
  stores: ResearchStore[];
  profiles: ResearchProfile[];
  selected_evidence: ResearchEvidenceSelection[];
  jobs: ResearchJob[];
  history: Array<Record<string, unknown>>;
  pipeline_assignment: PipelineAssignment | null;
  pipeline_options: Array<PipelineDefinition & { assigned?: boolean }>;
  pipeline_strategies: PipelineStrategy[];
  pipeline_override_allowed: boolean;
  can_run: boolean;
  can_select_evidence: boolean;
  can_manage_jobs: boolean;
  is_researcher: boolean;
};

export type ResponseFaqRecord = {
  record_id?: string;
  question?: string;
  text?: string;
  instructions?: string;
  provider?: string;
  model?: string;
  created_at?: string;
  updated_at?: string;
  evidence_count?: number;
  evidence?: ResearchResultEvidence[];
  retrieval?: Record<string, unknown>;
  query_metadata?: Record<string, unknown>;
  rag_request?: Record<string, unknown>;
  grade?: Record<string, unknown>;
  grades?: Array<Record<string, unknown>>;
  warnings?: string[];
  elapsed_seconds?: number;
};

export type ResponseFaqPage = {
  records: ResponseFaqRecord[];
  count: number;
  total: number;
  limit: number;
  offset: number;
  query?: string;
  exists?: boolean;
};
