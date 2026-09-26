/* Copyright 2026 Aaron John Schlosser, PhD. */
export type SettingsSectionId =
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
export type EmbeddingProvider =
  | "ollama"
  | "chroma"
  | "precomputed"
  | `profile:${string}`;
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
  k: number;
  fetch_k: number;
  lambda_mult: number;
  rrf_k: number;
  rerank_top_n: number;
  reranker: Reranker;
  cross_encoder_model: string;
  query_decomposition_num_predict: number;
  response_language: ResponseLanguage;
  evidence_record_char_limit: number;
  evidence_total_char_limit: number;
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

export const SETTINGS_SECTIONS: Array<{
  id: SettingsSectionId;
  labelKey: string;
  labelFallback: string;
  descriptionKey: string;
  descriptionFallback: string;
}> = [
  {
    id: "workspace",
    labelKey: "settings.nav.workspace",
    labelFallback: "Workspace and appearance",
    descriptionKey: "settings.nav.workspace_help",
    descriptionFallback: "Theme, color scheme, and contrast for this browser.",
  },
  {
    id: "language",
    labelKey: "settings.nav.language",
    labelFallback: "Language and accessibility",
    descriptionKey: "settings.nav.language_help",
    descriptionFallback: "Interface language and reading preferences.",
  },
  {
    id: "research",
    labelKey: "settings.nav.research",
    labelFallback: "Research defaults",
    descriptionKey: "settings.nav.research_help",
    descriptionFallback: "Starting points for evidence-grounded research runs.",
  },
  {
    id: "review",
    labelKey: "settings.nav.review",
    labelFallback: "Review and AI behavior",
    descriptionKey: "settings.nav.review_help",
    descriptionFallback: "Default provider, review preset, and how LLM review runs.",
  },
  {
    id: "providers",
    labelKey: "settings.nav.providers",
    labelFallback: "Providers and models",
    descriptionKey: "settings.nav.providers_help",
    descriptionFallback: "Endpoints, models, and concurrency live on the Providers page.",
  },
  {
    id: "retrieval",
    labelKey: "settings.nav.retrieval",
    labelFallback: "Vector stores and retrieval",
    descriptionKey: "settings.nav.retrieval_help",
    descriptionFallback: "Embedding defaults and RAG retrieval budgets.",
  },
  {
    id: "security",
    labelKey: "settings.nav.security",
    labelFallback: "Security, users, and permissions",
    descriptionKey: "settings.nav.security_help",
    descriptionFallback: "Accounts and role capabilities are managed on dedicated pages.",
  },
  {
    id: "system",
    labelKey: "settings.nav.system",
    labelFallback: "System and operations",
    descriptionKey: "settings.nav.system_help",
    descriptionFallback: "Backup, restore, workspace reset, and destructive controls.",
  },
];

export const SETTINGS_FIELDS: SettingsFieldIndex[] = [
  {
    id: "theme",
    section: "workspace",
    labelKey: "settings.color_theme",
    labelFallback: "Color theme",
    helpKey: "settings.appearance_help",
    helpFallback: "Choose the interface color theme for your workspace.",
  },
  {
    id: "scheme",
    section: "workspace",
    labelKey: "settings.color_scheme",
    labelFallback: "Color scheme",
    helpKey: "settings.color_scheme_help",
    helpFallback: "Light, dark, or follow this device. Stored in this browser.",
  },
  {
    id: "contrast",
    section: "workspace",
    labelKey: "settings.contrast",
    labelFallback: "Contrast",
    helpKey: "settings.contrast_help",
    helpFallback: "Increase contrast for borders and muted text in this workspace.",
  },
  {
    id: "about",
    section: "workspace",
    labelKey: "about.title",
    labelFallback: "About DerridAI",
    helpKey: "about.help",
    helpFallback:
      "Release version of this instance. The git commit is shown for administrators and on the sign-in screen.",
  },
  {
    id: "locale",
    section: "language",
    labelKey: "settings.interface_language",
    labelFallback: "Interface language",
    helpKey: "settings.interface_language_help",
    helpFallback: "Applies immediately to labels, dates, and numbers in this browser.",
  },
  {
    id: "review-provider",
    section: "review",
    labelKey: "settings.default_provider",
    labelFallback: "Default provider profile",
  },
  {
    id: "review-preset",
    section: "review",
    labelKey: "settings.review_preset",
    labelFallback: "Default review preset",
  },
  {
    id: "review-mode",
    section: "review",
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
    section: "review",
    labelKey: "settings.rag_auto_grade",
    labelFallback: "Auto-grade cached research answers",
  },
  {
    id: "notifications",
    section: "system",
    labelKey: "settings.desktop_notifications",
    labelFallback: "Desktop notifications",
  },
  {
    id: "backup",
    section: "system",
    labelKey: "settings.backup",
    labelFallback: "Backup and restore",
  },
  {
    id: "nuke",
    section: "system",
    labelKey: "config.nuke.title",
    labelFallback: "Start from scratch",
  },
];

export const RAG_DEFAULTS: RagSettingsDraft = {
  k: 64,
  fetch_k: 500,
  lambda_mult: 0.7,
  rrf_k: 60,
  rerank_top_n: 24,
  reranker: "cross_encoder",
  cross_encoder_model: "cross-encoder/ms-marco-MiniLM-L-6-v2",
  query_decomposition_num_predict: 768,
  response_language: "auto",
  evidence_record_char_limit: 12000,
  evidence_total_char_limit: 120000,
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
  const provider: EmbeddingProvider =
    rawProvider === "chroma" ||
    rawProvider === "precomputed" ||
    rawProvider === "ollama" ||
    rawProvider.startsWith("profile:")
      ? (rawProvider as EmbeddingProvider)
      : "ollama";
  const requestedModel = String(source?.embedding_model || "").trim();
  return {
    embedding_provider: provider,
    embedding_model:
      provider === "chroma" || provider === "precomputed"
        ? ""
        : requestedModel || "bge-m3:latest",
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
  return {
    k: Math.max(1, Math.min(500, finiteNumber(source?.k, RAG_DEFAULTS.k))),
    fetch_k: Math.max(1, Math.min(5000, finiteNumber(source?.fetch_k, RAG_DEFAULTS.fetch_k))),
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
