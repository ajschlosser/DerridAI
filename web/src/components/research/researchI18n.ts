import type { ResearchJob } from "../../types/research";

type Translate = (key: string, fallback?: string) => string;

const STAGE_ALIASES: Record<string, string> = {
  queued: "queued",
  waiting_for_ollama_slot: "queued",
  ollama_slot_acquired: "starting",
  ollama_slot_released: "completed",
  running: "starting",
  starting: "starting",
  query_metadata: "query_metadata",
  query_metadata_inference: "query_metadata",
  retrieval: "retrieval",
  retrieve: "retrieval",
  deduplicate: "deduplicate",
  deduplication: "deduplicate",
  rerank: "rerank",
  reranking: "rerank",
  context: "context",
  evidence: "context",
  evidence_packaging: "context",
  generation: "generation",
  generate: "generation",
  bind_sources: "bind_sources",
  source_binding: "bind_sources",
  response_cache: "response_cache",
  auto_grade: "auto_grade",
  grading: "auto_grade",
  completed: "completed",
  complete: "completed",
  cancelled: "cancelled",
  canceled: "cancelled",
  failed: "failed",
};

function normalizeStage(value: unknown): string {
  return String(value || "")
    .trim()
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function researchStageLabel(stage: unknown, t: Translate, locale = "en-US"): string {
  const normalized = normalizeStage(stage);
  const canonical = STAGE_ALIASES[normalized] || normalized;
  const labels: Record<string, [string, string]> = {
    queued: ["research.stage_queued", "Waiting for an execution slot"],
    starting: ["research.stage_starting", "Starting the Research pipeline"],
    query_metadata: ["research.stage_query_metadata", "Interpreting the question"],
    retrieval: ["research.stage_retrieval", "Retrieving candidate evidence"],
    deduplicate: ["research.stage_deduplicate", "Deduplicating evidence"],
    rerank: ["research.stage_rerank", "Reranking candidate evidence"],
    context: ["research.stage_context", "Packaging evidence context"],
    generation: ["research.stage_generation", "Generating the answer"],
    bind_sources: ["research.stage_bind_sources", "Binding claims to sources"],
    response_cache: ["research.stage_response_cache", "Writing the response cache"],
    auto_grade: ["research.stage_auto_grade", "Evaluating the answer"],
    completed: ["research.stage_completed", "Research complete"],
    cancelled: ["research.stage_cancelled", "Research cancelled"],
    failed: ["research.stage_failed", "Research failed"],
  };
  const match = labels[canonical];
  if (match) return t(match[0]);
  // English may safely retain a server-provided stage name. For French and any
  // other localized UI, avoid leaking an untranslated English implementation
  // label into the workspace.
  return locale === "en-US" && String(stage || "").trim()
    ? String(stage)
    : t("research.pipeline_stage");
}

export function researchJobDetail(job: ResearchJob, t: Translate, locale = "en-US"): string {
  if (locale === "en-US" && String(job.stage_detail || "").trim()) return String(job.stage_detail);
  return researchStageLabel(job.stage || job.status, t, locale);
}
