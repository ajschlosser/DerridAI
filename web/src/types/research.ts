export type ResearchStore = {
  name: string;
  count: number;
  collection_role?: string;
  embedding_model?: string;
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

export type ResearchConfig = {
  source_collection: string;
  locales: string[];
  search_types: string[];
  k: number;
  fetch_k: number;
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
