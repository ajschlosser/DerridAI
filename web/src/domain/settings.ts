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

export type SettingsSectionId =
  | "overview"
  | "preferences"
  | "research"
  | "retrieval"
  | "services"
  | "data"
  | "access"
  | "troubleshooting";

export type LegacySettingsSectionId =
  | "workspace"
  | "language"
  | "research"
  | "review"
  | "providers"
  | "retrieval"
  | "security"
  | "system";

export type SaveStatus = "saved" | "dirty" | "saving" | "success" | "failed" | "readonly";
export type PersistenceKind = "browser" | "session" | "backend" | "readonly" | "link";
export type ColorTheme = "green" | "blue" | "slate";
export type ColorScheme = "system" | "light" | "dark";
export type ContrastPref = "system" | "more";
export type ReviewPreset = "text" | "attribution" | "semantic";
export type LlmRunMode = "foreground" | "background";
export type EmbeddingProvider = "ollama" | "chroma" | "precomputed" | `profile:${string}`;
export type Reranker = "cross_encoder" | "lexical" | "none";
export type ResponseLanguage = "auto" | "en" | "fr";
export type RetrievalRoute = "similarity" | "lexical" | "mmr";

export interface SettingsFieldIndex {
  id: string;
  section: SettingsSectionId;
  labelKey: string;
  labelFallback: string;
  helpKey?: string;
  helpFallback?: string;
  keywords?: string[];
  advanced?: boolean;
  targetId?: string;
}

export interface ReviewSettingsDraft {
  default_provider_profile: string;
  default_review_preset: ReviewPreset;
  default_llm_run_mode: LlmRunMode;
}

export interface EmbeddingSettingsDraft {
  embedding_provider: EmbeddingProvider;
  embedding_model: string;
}

export interface RagSettingsDraft {
  source_collection: string;
  k: number;
  fetch_k: number;
  automatic_sizing: boolean;
  lambda_mult: number;
  rrf_k: number;
  rerank_top_n: number;
  reranker: Reranker;
  cross_encoder_model: string;
  query_decomposition_num_predict: number;
  response_language: ResponseLanguage;
  evidence_record_char_limit: number;
  evidence_total_char_limit: number;
  work_filter: string[];
  locales: string[];
  search_types: RetrievalRoute[];
  auto_grade: boolean;
}

export interface AppearanceSettingsDraft {
  ui_color_theme: ColorTheme;
  ui_color_scheme: ColorScheme;
  ui_contrast: ContrastPref;
}

export interface FieldError {
  field: string;
  messageKey: string;
  messageFallback: string;
}

export interface SettingsSectionDefinition {
  id: SettingsSectionId;
  labelKey: string;
  labelFallback: string;
  descriptionKey: string;
  descriptionFallback: string;
  adminOnly?: boolean;
}

export const SETTINGS_SECTIONS: SettingsSectionDefinition[] = [
  {
    id: "overview",
    labelKey: "settings.nav.overview",
    labelFallback: "Overview",
    descriptionKey: "settings.nav.overview_help",
    descriptionFallback:
      "Find settings by task, review important defaults, and jump to related workspaces.",
  },
  {
    id: "preferences",
    labelKey: "settings.nav.preferences",
    labelFallback: "Preferences",
    descriptionKey: "settings.nav.preferences_help",
    descriptionFallback:
      "Appearance, interface language, accessibility, notifications, and viewer behavior.",
  },
  {
    id: "research",
    labelKey: "settings.nav.research_review",
    labelFallback: "Research & review",
    descriptionKey: "settings.nav.research_review_help",
    descriptionFallback: "Defaults for research output, review execution, and evaluation behavior.",
  },
  {
    id: "retrieval",
    labelKey: "settings.nav.retrieval_indexing",
    labelFallback: "Retrieval & indexing",
    descriptionKey: "settings.nav.retrieval_indexing_help",
    descriptionFallback:
      "Embedding defaults, retrieval strategy, reranking, evidence budgets, and scope.",
    adminOnly: true,
  },
  {
    id: "services",
    labelKey: "settings.nav.ai_language_services",
    labelFallback: "AI & language services",
    descriptionKey: "settings.nav.ai_language_services_help",
    descriptionFallback: "Provider health, audio transcription, and document NLP resources.",
    adminOnly: true,
  },
  {
    id: "data",
    labelKey: "settings.nav.data_storage",
    labelFallback: "Data & storage",
    descriptionKey: "settings.nav.data_storage_help",
    descriptionFallback: "Retention, backup and restore, and links to system and corpus data.",
    adminOnly: true,
  },
  {
    id: "access",
    labelKey: "settings.nav.access_permissions",
    labelFallback: "Access & permissions",
    descriptionKey: "settings.nav.access_permissions_help",
    descriptionFallback: "Users, roles, and capability management.",
    adminOnly: true,
  },
  {
    id: "troubleshooting",
    labelKey: "settings.nav.troubleshooting",
    labelFallback: "Troubleshooting & recovery",
    descriptionKey: "settings.nav.troubleshooting_help",
    descriptionFallback: "Interface recovery, local cleanup, and destructive workspace reset.",
    adminOnly: true,
  },
];

export const SETTINGS_SECTION_ALIASES: Record<LegacySettingsSectionId, SettingsSectionId> = {
  workspace: "preferences",
  language: "preferences",
  research: "research",
  review: "research",
  providers: "services",
  retrieval: "retrieval",
  security: "access",
  system: "data",
};

export function resolveSettingsSectionId(value: string): SettingsSectionId | null {
  if (SETTINGS_SECTIONS.some((section) => section.id === value)) return value as SettingsSectionId;
  return SETTINGS_SECTION_ALIASES[value as LegacySettingsSectionId] || null;
}

export const SETTINGS_FIELDS: SettingsFieldIndex[] = [
  {
    id: "theme",
    section: "preferences",
    labelKey: "settings.color_theme",
    labelFallback: "Color theme",
    helpKey: "settings.appearance_help",
    helpFallback: "Choose the interface color theme for your workspace.",
    targetId: "settings-heading-workspace",
  },
  {
    id: "scheme",
    section: "preferences",
    labelKey: "settings.color_scheme",
    labelFallback: "Color scheme",
    helpKey: "settings.color_scheme_help",
    helpFallback: "Light, dark, or follow this device. Stored in this browser.",
  },
  {
    id: "contrast",
    section: "preferences",
    labelKey: "settings.contrast",
    labelFallback: "Contrast",
    helpKey: "settings.contrast_help",
    helpFallback: "Increase contrast for borders and muted text in this workspace.",
  },
  {
    id: "about",
    section: "overview",
    labelKey: "about.title",
    labelFallback: "About DerridAI",
    helpKey: "about.help",
    helpFallback:
      "Release version of this instance. The git commit is shown for administrators and on the sign-in screen.",
    targetId: "settings-overview-title",
  },
  {
    id: "locale",
    section: "preferences",
    labelKey: "settings.interface_language",
    labelFallback: "Interface language",
    helpKey: "settings.interface_language_help",
    helpFallback: "Applies immediately to labels, dates, and numbers in this browser.",
  },
  {
    id: "review-provider",
    section: "research",
    labelKey: "settings.default_provider",
    labelFallback: "Default provider profile",
  },
  {
    id: "review-preset",
    section: "research",
    labelKey: "settings.review_preset",
    labelFallback: "Default review preset",
  },
  {
    id: "review-mode",
    section: "research",
    labelKey: "settings.run_mode",
    labelFallback: "Default run mode",
  },
  {
    id: "embedding-provider",
    section: "retrieval",
    labelKey: "settings.embedding_provider",
    labelFallback: "Default embedding provider",
  },
  {
    id: "embedding-model",
    section: "retrieval",
    labelKey: "settings.embedding_model",
    labelFallback: "Default embedding model",
  },
  {
    id: "chroma-path",
    section: "retrieval",
    labelKey: "settings.chroma_path",
    labelFallback: "Current Chroma path",
  },
  {
    id: "rag-database",
    section: "retrieval",
    labelKey: "settings.rag_database",
    labelFallback: "Default corpus database",
    helpKey: "settings.rag_database_help",
    helpFallback: "Choose which corpus database supplies the default Research work scope.",
    keywords: ["database", "collection", "corpus", "research scope"],
  },
  {
    id: "rag-k",
    section: "retrieval",
    labelKey: "settings.rag_k",
    labelFallback: "Retrieval k",
    helpKey: "settings.rag_k_help",
    helpFallback: "How many passages to keep after ranking. Typical scholarly runs use 24–64.",
  },
  {
    id: "rag-fetch-k",
    section: "retrieval",
    labelKey: "settings.rag_fetch_k",
    labelFallback: "MMR fetch_k",
    advanced: true,
  },
  {
    id: "rag-lambda",
    section: "retrieval",
    labelKey: "settings.rag_lambda",
    labelFallback: "MMR lambda",
    advanced: true,
  },
  {
    id: "rag-rrf",
    section: "retrieval",
    labelKey: "settings.rag_rrf_k",
    labelFallback: "RRF k",
    advanced: true,
  },
  {
    id: "rag-top-n",
    section: "retrieval",
    labelKey: "settings.rag_top_n",
    labelFallback: "Rerank top N",
  },
  {
    id: "rag-reranker",
    section: "retrieval",
    labelKey: "settings.rag_reranker",
    labelFallback: "Default reranker",
  },
  {
    id: "rag-cross-encoder",
    section: "retrieval",
    labelKey: "settings.rag_cross_encoder",
    labelFallback: "Cross-encoder model",
    advanced: true,
  },
  {
    id: "rag-decompose",
    section: "retrieval",
    labelKey: "settings.rag_decompose",
    labelFallback: "Query-decomposition max tokens",
    advanced: true,
  },
  {
    id: "rag-response-language",
    section: "research",
    labelKey: "settings.rag_response_language",
    labelFallback: "Response language",
  },
  {
    id: "rag-automatic-sizing",
    section: "retrieval",
    labelKey: "settings.rag_automatic_sizing",
    labelFallback: "Automatic sizing",
    helpKey: "settings.rag_automatic_sizing_help",
    helpFallback:
      "Adapt retrieval depth to median Record size and restore bounded same-document context without raising reranker or evidence-budget caps.",
    keywords: ["record size", "automatic", "neighbors", "retrieval depth", "segmentation"],
  },
  {
    id: "rag-record-chars",
    section: "retrieval",
    labelKey: "settings.rag_record_chars",
    labelFallback: "Max characters per evidence record",
    helpKey: "settings.rag_record_chars_help",
    helpFallback:
      "Caps each passage so the model cannot swallow an entire chapter as one evidence item.",
  },
  {
    id: "rag-total-chars",
    section: "retrieval",
    labelKey: "settings.rag_total_chars",
    labelFallback: "Total evidence characters",
  },
  {
    id: "rag-works",
    section: "retrieval",
    labelKey: "settings.rag_works",
    labelFallback: "Works to include",
    helpKey: "settings.rag_works_help",
    helpFallback: "Restrict Research retrieval to selected works. Leave empty to include all works.",
    keywords: ["works", "scope", "filter", "research corpus"],
  },
  {
    id: "rag-locales",
    section: "retrieval",
    labelKey: "settings.rag_locales",
    labelFallback: "Document languages",
  },
  {
    id: "rag-routes",
    section: "retrieval",
    labelKey: "settings.rag_routes",
    labelFallback: "Retrieval routes",
  },
  {
    id: "rag-auto-grade",
    section: "research",
    labelKey: "settings.rag_auto_grade",
    labelFallback: "Auto-grade cached research answers",
  },
  {
    id: "notifications",
    section: "preferences",
    labelKey: "settings.desktop_notifications",
    labelFallback: "Desktop notifications",
  },
  {
    id: "data-workspaces",
    section: "data",
    labelKey: "settings.data_workspaces_title",
    labelFallback: "Data workspaces",
    helpKey: "settings.data_workspaces_help",
    helpFallback:
      "Inspect operational System Data or open Corpus Data without duplicating those workspaces inside Settings.",
    keywords: ["system data", "corpus data", "databases", "stores", "vector stores"],
    targetId: "settings-heading-data-workspaces",
  },
  {
    id: "data-retention",
    section: "data",
    labelKey: "settings.retention_title",
    labelFallback: "Data retention",
    helpKey: "settings.retention_help",
    helpFallback:
      "Choose how long DerridAI keeps operational history: pipeline traces, benchmark results, finished jobs, and saved Research responses.",
    keywords: ["retention", "expire", "traces", "job history", "disk space", "gigabytes"],
    targetId: "settings-heading-data-retention",
  },
  {
    id: "backup",
    section: "data",
    labelKey: "settings.backup",
    labelFallback: "Backup and restore",
    targetId: "settings-heading-backup",
  },
  {
    id: "nuke",
    section: "troubleshooting",
    labelKey: "config.nuke.title",
    labelFallback: "Start from scratch",
  },
  {
    id: "providers",
    section: "services",
    labelKey: "settings.providers_title",
    labelFallback: "Provider status",
    helpKey: "settings.providers_help",
    helpFallback:
      "Review configured LLM provider health and open the Providers workspace to manage profiles.",
    keywords: ["provider", "model", "ollama", "openai", "health"],
    targetId: "settings-section-providers",
  },
  {
    id: "audio",
    section: "services",
    labelKey: "settings.audio_title",
    labelFallback: "Audio transcription",
    helpKey: "settings.audio_help",
    helpFallback: "Configure and test the audio transcription service used for media ingestion.",
    keywords: ["audio", "transcription", "speech", "api key", "model"],
    targetId: "settings-heading-audio",
  },
  {
    id: "nlp-packs",
    section: "services",
    labelKey: "settings.nlp_packs_title",
    labelFallback: "Document NLP resources",
    helpKey: "settings.nlp_packs_help",
    helpFallback: "Install and manage language resources used for document NLP.",
    keywords: ["nlp", "language pack", "pos", "ner", "spacy"],
    targetId: "settings-heading-language-packs",
  },
  {
    id: "access",
    section: "access",
    labelKey: "settings.security_title",
    labelFallback: "Users, roles, and permissions",
    helpKey: "settings.security_help",
    helpFallback: "Open the dedicated Users and Roles workspaces to manage access.",
    keywords: ["users", "roles", "permissions", "capabilities", "access"],
    targetId: "settings-heading-security",
  },
  {
    id: "interface-reset",
    section: "troubleshooting",
    labelKey: "settings.viewer_title",
    labelFallback: "Interface recovery",
    helpKey: "settings.viewer_help",
    helpFallback: "Reset local table, panel, sidebar, and update-history state.",
    keywords: ["reset", "columns", "panels", "sidebar", "updates", "upsert"],
    targetId: "settings-heading-viewer",
  },
];

export const RAG_DEFAULTS: RagSettingsDraft = {
  source_collection: "",
  k: 64,
  fetch_k: 500,
  automatic_sizing: false,
  lambda_mult: 0.7,
  rrf_k: 60,
  rerank_top_n: 24,
  reranker: "cross_encoder",
  cross_encoder_model: "cross-encoder/ms-marco-MiniLM-L-6-v2",
  query_decomposition_num_predict: 768,
  response_language: "auto",
  evidence_record_char_limit: 12000,
  evidence_total_char_limit: 120000,
  work_filter: [],
  locales: ["en", "fr"],
  search_types: ["similarity", "lexical", "mmr"],
  auto_grade: false,
};

export const APPEARANCE_DEFAULTS: AppearanceSettingsDraft = {
  ui_color_theme: "green",
  ui_color_scheme: "system",
  ui_contrast: "system",
};

export function isSettingsSectionId(value: string): value is SettingsSectionId {
  return SETTINGS_SECTIONS.some((section) => section.id === value);
}

export function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function sameSettings(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function normalizeReview(
  source: Partial<ReviewSettingsDraft> | null | undefined,
): ReviewSettingsDraft {
  const preset = source?.default_review_preset;
  const mode = source?.default_llm_run_mode;
  return {
    default_provider_profile: String(source?.default_provider_profile || ""),
    default_review_preset: preset === "attribution" || preset === "semantic" ? preset : "text",
    default_llm_run_mode: mode === "background" ? "background" : "foreground",
  };
}

export function normalizeEmbedding(
  source: Partial<EmbeddingSettingsDraft> | null | undefined,
): EmbeddingSettingsDraft {
  const rawProvider = String(source?.embedding_provider || "").trim();
  let provider: EmbeddingProvider = "ollama";
  if (
    rawProvider === "chroma" ||
    rawProvider === "precomputed" ||
    rawProvider === "ollama" ||
    rawProvider.startsWith("profile:")
  ) {
    provider = rawProvider as EmbeddingProvider;
  }

  const requestedModel = String(source?.embedding_model || "").trim();
  let embeddingModel = requestedModel || "bge-m3:latest";
  if (provider === "chroma" || provider === "precomputed") embeddingModel = "";

  return {
    embedding_provider: provider,
    embedding_model: embeddingModel,
  };
}

export function normalizeAppearance(
  source: Partial<AppearanceSettingsDraft> | null | undefined,
): AppearanceSettingsDraft {
  const theme = source?.ui_color_theme;
  const scheme = source?.ui_color_scheme;
  const contrast = source?.ui_contrast;
  return {
    ui_color_theme: theme === "blue" || theme === "slate" ? theme : "green",
    ui_color_scheme: scheme === "light" || scheme === "dark" ? scheme : "system",
    ui_contrast: contrast === "more" ? "more" : "system",
  };
}

function finiteNumber(value: unknown, fallback: number): number {
  const next = Number(value);
  return Number.isFinite(next) ? next : fallback;
}

export function normalizeRag(
  source: Partial<RagSettingsDraft> | null | undefined,
): RagSettingsDraft {
  const reranker = source?.reranker;
  const language = source?.response_language;
  const locales = Array.isArray(source?.locales)
    ? source.locales.filter((code): code is string => code === "en" || code === "fr")
    : [...RAG_DEFAULTS.locales];
  const routes = Array.isArray(source?.search_types)
    ? source.search_types.filter(
        (route): route is RetrievalRoute =>
          route === "similarity" || route === "lexical" || route === "mmr",
      )
    : [...RAG_DEFAULTS.search_types];
  const workFilter = Array.isArray(source?.work_filter)
    ? [
        ...new Set(
          source.work_filter
            .map((work) => String(work || "").trim())
            .filter((work) => Boolean(work) && work.length <= 500),
        ),
      ].slice(0, 500)
    : [];
  return {
    source_collection: String(source?.source_collection || "").trim(),
    k: Math.max(1, Math.min(500, finiteNumber(source?.k, RAG_DEFAULTS.k))),
    fetch_k: Math.max(1, Math.min(5000, finiteNumber(source?.fetch_k, RAG_DEFAULTS.fetch_k))),
    automatic_sizing: Boolean(source?.automatic_sizing),
    lambda_mult: Math.max(
      0,
      Math.min(1, finiteNumber(source?.lambda_mult, RAG_DEFAULTS.lambda_mult)),
    ),
    rrf_k: Math.max(1, finiteNumber(source?.rrf_k, RAG_DEFAULTS.rrf_k)),
    rerank_top_n: Math.max(
      1,
      Math.min(500, finiteNumber(source?.rerank_top_n, RAG_DEFAULTS.rerank_top_n)),
    ),
    reranker: reranker === "lexical" || reranker === "none" ? reranker : "cross_encoder",
    cross_encoder_model:
      String(source?.cross_encoder_model || RAG_DEFAULTS.cross_encoder_model).trim() ||
      RAG_DEFAULTS.cross_encoder_model,
    query_decomposition_num_predict: Math.max(
      64,
      finiteNumber(
        source?.query_decomposition_num_predict,
        RAG_DEFAULTS.query_decomposition_num_predict,
      ),
    ),
    response_language: language === "en" || language === "fr" ? language : "auto",
    evidence_record_char_limit: Math.max(
      500,
      finiteNumber(source?.evidence_record_char_limit, RAG_DEFAULTS.evidence_record_char_limit),
    ),
    evidence_total_char_limit: Math.max(
      5000,
      finiteNumber(source?.evidence_total_char_limit, RAG_DEFAULTS.evidence_total_char_limit),
    ),
    work_filter: workFilter,
    locales,
    search_types: routes,
    auto_grade: Boolean(source?.auto_grade),
  };
}

export function validateRag(draft: RagSettingsDraft): FieldError[] {
  const errors: FieldError[] = [];
  if (!draft.locales.length)
    errors.push({
      field: "locales",
      messageKey: "settings.error.rag_locales",
      messageFallback: "Select at least one document language.",
    });
  if (!draft.search_types.length)
    errors.push({
      field: "search_types",
      messageKey: "settings.error.rag_routes",
      messageFallback: "Select at least one retrieval route.",
    });
  if (draft.fetch_k < draft.k)
    errors.push({
      field: "fetch_k",
      messageKey: "settings.error.rag_fetch_k",
      messageFallback: "MMR fetch_k must be at least as large as retrieval k.",
    });
  if (draft.evidence_total_char_limit < draft.evidence_record_char_limit) {
    errors.push({
      field: "evidence_total_char_limit",
      messageKey: "settings.error.rag_total_chars",
      messageFallback: "Total evidence characters must be at least the per-record limit.",
    });
  }
  return errors;
}

export function filterSettingsFields(
  query: string,
  translate: (key: string, fallback: string) => string,
): SettingsFieldIndex[] {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) return SETTINGS_FIELDS;
  return SETTINGS_FIELDS.filter((field) => {
    const haystack = [
      translate(field.labelKey, field.labelFallback),
      field.helpKey ? translate(field.helpKey, field.helpFallback || "") : "",
      ...(field.keywords || []),
      field.id,
      field.section,
    ]
      .join(" ")
      .toLocaleLowerCase();
    return haystack.includes(needle);
  });
}

export function resolveColorScheme(pref: ColorScheme, systemDark: boolean): "light" | "dark" {
  if (pref === "light" || pref === "dark") return pref;
  return systemDark ? "dark" : "light";
}

export function resolveContrast(pref: ContrastPref, systemMore: boolean): "default" | "more" {
  if (pref === "more") return "more";
  return systemMore ? "more" : "default";
}
