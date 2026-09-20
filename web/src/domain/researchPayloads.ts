/* Copyright 2026 Aaron John Schlosser, PhD. */
import { cloneAuditValue } from "./recordValues";

// Shaping and validation of Research (RAG) data crossing the runtime/Vue boundary. Pure functions
// moved verbatim from the legacy runtime.

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

const PROFILE_KEYS = [
  "id",
  "name",
  "type",
  "model",
  "model_mode",
  "model_kind",
  "max_concurrent_requests",
  "num_ctx",
  "num_predict",
  "think",
  "temperature",
  "top_k",
  "top_p",
  "min_p",
  "repeat_penalty",
  "seed",
  "mirostat",
  "mirostat_eta",
  "mirostat_tau",
  "keep_alive",
  "extra_options",
];

export function researchProfileForUi(profile: Loose | null | undefined) {
  if (!profile) return null;
  return Object.fromEntries(
    PROFILE_KEYS.filter((key) => profile[key] !== undefined).map((key) => [
      key,
      cloneAuditValue(profile[key]),
    ]),
  );
}

export function researchEvidenceForUi(item: Loose | null | undefined) {
  if (!item) return null;
  return {
    key: item.key,
    kind: item.kind,
    collection: item.collection || null,
    chroma_id: item.chroma_id || null,
    record_id: item.record_id || "",
    work: item.work || "",
    page_start: item.page_start ?? null,
    page_end: item.page_end ?? null,
    speaker: item.speaker || null,
    position_holder: item.position_holder || null,
    stance: item.stance || null,
    discourse_role: item.discourse_role || null,
    target: item.target || null,
    proposition_status: item.proposition_status || null,
    inline_citation: item.inline_citation || null,
    text_preview: item.text_preview || "",
    label: item.label || "",
  };
}

export function researchJobForUi(job: Loose | null | undefined) {
  if (!job) return null;
  const result = job.result && typeof job.result === "object" ? job.result : null;
  return {
    id: job.id,
    type: job.type,
    status: job.status,
    stage: job.stage || "",
    stage_detail: job.stage_detail || "",
    prompt: job.prompt || result?.prompt || "",
    provider: job.provider || result?.provider || "",
    provider_profile_id: job.provider_profile_id || null,
    model: job.model || result?.model || "",
    source_collection: job.source_collection || "",
    owner: job.owner || "",
    created_at: job.created_at || null,
    started_at: job.started_at || null,
    finished_at: job.finished_at || null,
    updated_at: job.updated_at || null,
    completed: Number(job.completed || 0),
    total: Number(job.total || 0),
    cancel_requested: Boolean(job.cancel_requested),
    fatal_error: job.fatal_error || null,
    request: job.request ? cloneAuditValue(job.request) : null,
    result: result ? cloneAuditValue(result) : null,
    events: Array.isArray(job.events) ? cloneAuditValue(job.events) : [],
  };
}

interface NumberSpec {
  integer?: boolean;
  min?: number;
  max?: number;
}

export function finiteResearchNumber(
  value: unknown,
  fallback: number | null,
  { integer = false, min = -Infinity, max = Infinity }: NumberSpec = {},
): number | null {
  if (value === null || value === undefined || value === "") return fallback;
  const parsed = integer ? Number.parseInt(String(value), 10) : Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

export function sanitizeResearchGeneration(input: unknown = {}) {
  const source: Loose =
    input && typeof input === "object" && !Array.isArray(input) ? (input as Loose) : {};
  const out: Loose = {};
  const specs: Record<string, NumberSpec> = {
    num_ctx: { integer: true, min: 512, max: 262144 },
    num_predict: { integer: true, min: 16, max: 32768 },
    temperature: { min: 0, max: 2 },
    top_k: { integer: true, min: 0, max: 1000 },
    top_p: { min: 0, max: 1 },
    min_p: { min: 0, max: 1 },
    repeat_penalty: { min: 0, max: 5 },
    seed: { integer: true },
    mirostat: { integer: true, min: 0, max: 2 },
    mirostat_eta: { min: 0 },
    mirostat_tau: { min: 0 },
  };
  for (const [key, spec] of Object.entries(specs)) {
    const raw = source[key];
    if (raw === null || raw === undefined || raw === "") continue;
    const value = finiteResearchNumber(raw, null, spec);
    if (value !== null && Number.isFinite(value)) out[key] = value;
  }
  const think = source.think;
  if (typeof think === "boolean") out.think = think;
  else if (["low", "medium", "high"].includes(String(think || "").toLowerCase()))
    out.think = String(think).toLowerCase();
  else if (String(think || "").toLowerCase() === "true") out.think = true;
  else if (String(think || "").toLowerCase() === "false") out.think = false;
  if (
    source.keep_alive !== null &&
    source.keep_alive !== undefined &&
    String(source.keep_alive).trim()
  )
    out.keep_alive = String(source.keep_alive).trim();
  if (Array.isArray(source.stop))
    out.stop = source.stop.map((item) => String(item)).filter(Boolean);
  let extra = source.extra_options;
  if (typeof extra === "string") {
    try {
      extra = JSON.parse(extra || "{}");
    } catch {
      extra = {};
    }
  }
  out.extra_options = extra && typeof extra === "object" && !Array.isArray(extra) ? extra : {};
  return out;
}

export function normalizedResearchConfig(cfg: Loose = {}) {
  const locales = Array.isArray(cfg.locales)
    ? [...new Set(cfg.locales.map(String).filter((value) => ["en", "fr"].includes(value)))]
    : ["en", "fr"];
  const searchTypes = Array.isArray(cfg.search_types)
    ? [
        ...new Set(
          cfg.search_types
            .map(String)
            .filter((value) => ["mmr", "similarity", "lexical"].includes(value)),
        ),
      ]
    : ["similarity", "lexical", "mmr"];
  const reranker = ["cross_encoder", "lexical", "none"].includes(String(cfg.reranker || ""))
    ? String(cfg.reranker)
    : "cross_encoder";
  const responseLanguage = ["auto", "en", "fr"].includes(String(cfg.response_language || ""))
    ? String(cfg.response_language)
    : "auto";
  return {
    ...cfg,
    k: finiteResearchNumber(cfg.k, 64, { integer: true, min: 1, max: 500 }),
    fetch_k: finiteResearchNumber(cfg.fetch_k, 500, { integer: true, min: 1, max: 5000 }),
    lambda_mult: finiteResearchNumber(cfg.lambda_mult, 0.7, { min: 0, max: 1 }),
    rrf_k: finiteResearchNumber(cfg.rrf_k, 60, { integer: true, min: 1, max: 10000 }),
    rerank_top_n: finiteResearchNumber(cfg.rerank_top_n, 24, { integer: true, min: 1, max: 500 }),
    reranker,
    cross_encoder_model:
      String(cfg.cross_encoder_model || "cross-encoder/ms-marco-MiniLM-L-6-v2").trim() ||
      "cross-encoder/ms-marco-MiniLM-L-6-v2",
    query_decomposition: Boolean(cfg.query_decomposition),
    query_decomposition_num_predict: finiteResearchNumber(
      cfg.query_decomposition_num_predict,
      768,
      {
        integer: true,
        min: 64,
        max: 8192,
      },
    ),
    response_language: responseLanguage,
    evidence_record_char_limit: finiteResearchNumber(cfg.evidence_record_char_limit, 12000, {
      integer: true,
      min: 500,
      max: 100000,
    }),
    evidence_total_char_limit: finiteResearchNumber(cfg.evidence_total_char_limit, 120000, {
      integer: true,
      min: 5000,
      max: 1000000,
    }),
    locales,
    search_types: searchTypes,
    bind_citations: cfg.bind_citations !== false,
    include_works_cited: cfg.include_works_cited !== false,
    auto_grade: Boolean(cfg.auto_grade),
    skip_retrieval: Boolean(cfg.skip_retrieval),
  };
}
