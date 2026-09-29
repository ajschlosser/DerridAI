/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { PipelineDefinition } from "../types/pipelines";

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
