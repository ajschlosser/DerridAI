/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { PipelineDefinition, PipelineStrategy } from "../types/pipelines";

export type PipelineTranslator = (key: string, fallback: string) => string;

export function pipelineKey(pipeline: Pick<PipelineDefinition, "pipeline_id" | "version">) {
  return `${pipeline.pipeline_id}@${pipeline.version}`;
}

export function pipelinePurposeLabel(purpose: string, t: PipelineTranslator) {
  const labels: Record<string, string> = {
    research: t("pipelines.purpose_research", "Research"),
    evidence_suggestion: t("pipelines.purpose_evidence", "Evidence suggestion"),
    metadata_precedents: t("pipelines.purpose_precedents", "Metadata precedents"),
    claim_memory: t("pipelines.purpose_claim_memory", "Claim memory"),
    response_memory: t("pipelines.purpose_response_memory", "Response memory"),
  };
  return labels[purpose] || purpose;
}

export function pipelineDefinitionStatusLabel(
  status: PipelineDefinition["status"],
  t: PipelineTranslator,
) {
  const labels: Record<PipelineDefinition["status"], string> = {
    draft: t("pipelines.status_draft", "Draft"),
    active: t("pipelines.status_active", "Active"),
    disabled: t("pipelines.status_disabled", "Disabled"),
  };
  return labels[status];
}

export function pipelineRunStatusLabel(status: string, t: PipelineTranslator) {
  const labels: Record<string, string> = {
    completed: t("pipelines.status_completed", "Completed"),
    failed: t("pipelines.status_failed", "Failed"),
    cancelled: t("pipelines.status_cancelled", "Cancelled"),
    running: t("pipelines.status_running", "Running"),
  };
  return labels[status] || status;
}

export function formatPipelineDate(value: string | null | undefined, locale: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function pipelineStageFamilyLabel(family: string | null | undefined, t: PipelineTranslator) {
  const value = String(family || "");
  const labels: Record<string, string> = {
    query_transform: t("pipelines.family_query_transform", "Query transform"),
    candidate_generation: t("pipelines.family_candidate_generation", "Candidate generation"),
    filter: t("pipelines.family_filter", "Filter"),
    normalization: t("pipelines.family_normalization", "Normalization"),
    fusion: t("pipelines.family_fusion", "Fusion"),
    rerank: t("pipelines.family_rerank", "Reranking"),
    support_validation: t("pipelines.family_support_validation", "Support validation"),
    diversity: t("pipelines.family_diversity", "Diversity"),
    selection: t("pipelines.family_selection", "Selection"),
    context_pack: t("pipelines.family_context_pack", "Context packing"),
    llm: t("pipelines.family_llm", "LLM"),
    evaluation: t("pipelines.family_evaluation", "Evaluation"),
  };
  return labels[value] || value || t("pipelines.family_unknown", "Unknown");
}

export function pipelineEdgeKindLabel(kind: string, t: PipelineTranslator) {
  const labels: Record<string, string> = {
    next: t("pipelines.then", "then"),
    empty: t("pipelines.on_empty", "On empty"),
    unavailable: t("pipelines.on_unavailable", "On unavailable"),
    timeout: t("pipelines.on_timeout", "On timeout"),
    error: t("pipelines.on_error", "On error"),
  };
  return labels[kind] || kind;
}

export function pipelineStrategyLabel(
  strategy: PipelineStrategy | null | undefined,
  t: PipelineTranslator,
) {
  if (!strategy) return "";
  return strategy.label_key ? t(strategy.label_key, strategy.label) : strategy.label;
}

export function pipelineStrategyDescription(
  strategy: PipelineStrategy | null | undefined,
  t: PipelineTranslator,
) {
  if (!strategy) return "";
  return strategy.description_key
    ? t(strategy.description_key, strategy.description)
    : strategy.description;
}


export function pipelineConfigLabel(key: string, t: PipelineTranslator) {
  const labels: Record<string, string> = {
    fetch_k: t("pipelines.config.fetch_k.label", "Candidate pool size"),
    lambda_mult: t("pipelines.config.lambda_mult.label", "Relevance vs. variety"),
    limit: t("pipelines.config.limit.label", "Maximum items"),
    rrf_k: t("pipelines.config.rrf_k.label", "Rank-fusion constant"),
    top_k: t("pipelines.config.top_k.label", "Items to keep"),
    model: t("pipelines.config.model.label", "Reranking model"),
    timeout_seconds: t("pipelines.config.timeout_seconds.label", "Time limit (seconds)"),
    record_char_limit: t("pipelines.config.record_char_limit.label", "Text limit per record"),
    total_char_limit: t("pipelines.config.total_char_limit.label", "Total evidence text limit"),
    num_predict: t("pipelines.config.num_predict.label", "Maximum query-analysis tokens"),
    semantic_weight: t("pipelines.config.semantic_weight.label", "Semantic-search weight"),
    lexical_weight: t("pipelines.config.lexical_weight.label", "Word-match weight"),
    min_score: t("pipelines.config.min_score.label", "Minimum support score"),
  };
  return labels[key] || key.replaceAll("_", " ");
}

export function pipelineConfigHelp(key: string, t: PipelineTranslator) {
  const help: Record<string, string> = {
    fetch_k: t(
      "pipelines.config.fetch_k.help",
      "Technical name: fetch_k. This is how many possible matches the stage gathers before later stages narrow the list. A larger pool can improve recall, but it uses more time and memory.",
    ),
    lambda_mult: t(
      "pipelines.config.lambda_mult.help",
      "Technical name: lambda_mult. This controls the trade-off between relevance and variety. Values nearer 1 favor the most relevant passages; lower values allow more diverse sources into the result.",
    ),
    limit: t(
      "pipelines.config.limit.help",
      "Technical name: limit. This is the maximum number of items this stage may pass onward.",
    ),
    rrf_k: t(
      "pipelines.config.rrf_k.help",
      "Technical name: rrf_k. Reciprocal-rank fusion combines several ranked lists. This constant controls how strongly differences near the top of each list matter; changing it alters the fusion mathematics, not the number of results.",
    ),
    top_k: t(
      "pipelines.config.top_k.help",
      "Technical name: top_k. After this stage scores or orders candidates, only this many are retained for the next step.",
    ),
    model: t(
      "pipelines.config.model.help",
      "The technical model identifier used by this stage. For a cross-encoder, the model reads the query and each candidate together and gives each pair a relevance score.",
    ),
    timeout_seconds: t(
      "pipelines.config.timeout_seconds.help",
      "How long DerridAI waits for this stage before treating it as timed out. A configured timeout fallback can take over when this limit is reached.",
    ),
    record_char_limit: t(
      "pipelines.config.record_char_limit.help",
      "Maximum text characters taken from any one evidence record when building the model's context. This prevents a single long record from crowding out the rest.",
    ),
    total_char_limit: t(
      "pipelines.config.total_char_limit.help",
      "Maximum combined text characters in the evidence packet sent to the answer-generation model.",
    ),
    num_predict: t(
      "pipelines.config.num_predict.help",
      "Maximum number of tokens the model may generate while analyzing or decomposing the research question before retrieval begins.",
    ),
    semantic_weight: t(
      "pipelines.config.semantic_weight.help",
      "How much the combined score should depend on semantic similarity: similarity in meaning, even when the wording is different.",
    ),
    lexical_weight: t(
      "pipelines.config.lexical_weight.help",
      "How much the combined score should depend on lexical similarity: overlap in words or phrases.",
    ),
    min_score: t(
      "pipelines.config.min_score.help",
      "The lowest support score a candidate may have and still pass this validation stage.",
    ),
  };
  return (
    help[key] ||
    t(
      "pipelines.config.generic_help",
      "This is a server-declared technical setting for the selected strategy. Changing it changes how this stage behaves; validation checks its allowed type and range before the pipeline can be used.",
    )
  );
}

export function pipelineDataTypeHelp(value: string, t: PipelineTranslator) {
  const help: Record<string, string> = {
    query: t(
      "pipelines.data_type.query_help",
      "A research question or search expression before candidate passages have been retrieved.",
    ),
    candidate_set: t(
      "pipelines.data_type.candidate_set_help",
      "A working list of possible records or passages. Later stages can reorder, filter, validate, or reduce this list.",
    ),
    context_packet: t(
      "pipelines.data_type.context_packet_help",
      "A bounded evidence bundle prepared for a language model, including the text and provenance needed for citation-aware generation.",
    ),
    model_output: t(
      "pipelines.data_type.model_output_help",
      "Text or structured content produced by a language model.",
    ),
    evaluation: t(
      "pipelines.data_type.evaluation_help",
      "A grading or assessment result produced after the main answer.",
    ),
  };
  return (
    help[value] ||
    t(
      "pipelines.data_type.generic_help",
      "This is the technical data shape passed between pipeline stages.",
    )
  );
}
