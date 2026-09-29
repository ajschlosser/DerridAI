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
