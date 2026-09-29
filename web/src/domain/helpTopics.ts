/* Copyright 2026 Aaron John Schlosser, PhD. */
/**
 * Help Center information architecture. The domain file owns only stable IDs,
 * route bindings, visibility rules, and search composition. User-facing copy
 * lives in the locale dictionaries so English and French stay in parity.
 */

export type HelpTranslate = (key: string, fallback?: string) => string;

export interface HelpQuestionDefinition {
  id: string;
  /**
   * Reserve downstream-impact callouts for actions whose consequences are not
   * already obvious from the answer. Explanatory FAQs should stay concise.
   */
  showImpact?: boolean;
}

export interface HelpSection {
  id: string;
  /** Corpus-review topics describe administrator-only workflows. */
  adminOnly?: boolean;
  questions: HelpQuestionDefinition[];
}

export interface HelpEntry {
  id: string;
  question: string;
  answer: string;
  impact?: string;
}

export interface HelpPageGuideDefinition {
  id: string;
  routeName: string;
  path: string;
  group: HelpPageGroup;
  adminOnly?: boolean;
  capability?: string;
  /** Show a downstream-effects callout only when this page can persist or configure state. */
  showImpact?: boolean;
}

export interface HelpPageGuide extends HelpPageGuideDefinition {
  title: string;
  summary: string;
  tasks: string;
  impact?: string;
}

export type HelpPageGroup =
  | "overview"
  | "research"
  | "corpora"
  | "corpus_management"
  | "ai_automation"
  | "system"
  | "support";

export type HelpGlossaryCategory =
  | "all"
  | "ai"
  | "retrieval"
  | "parameters"
  | "provenance"
  | "storage";

export interface HelpGlossaryDefinition {
  id: string;
  category: Exclude<HelpGlossaryCategory, "all">;
  code?: boolean;
  aliases?: string[];
}

export interface HelpGlossaryEntry extends HelpGlossaryDefinition {
  term: string;
  definition: string;
  practical: string;
}

export const HELP_SECTIONS: HelpSection[] = [
  {
    id: "basics",
    questions: [{ id: "what_is" }, { id: "authoritative" }, { id: "citations" }],
  },
  {
    id: "getting_started",
    questions: [
      { id: "search_vs_research" },
      { id: "find_records" },
      { id: "search_no_results" },
      { id: "select_evidence", showImpact: true },
    ],
  },
  {
    id: "research",
    questions: [
      { id: "retrieval_modes" },
      { id: "no_citations" },
      { id: "rerun_answer" },
      { id: "choose_model" },
      { id: "cached_responses", showImpact: true },
      { id: "cached_provenance", showImpact: true },
      { id: "validate_claims", showImpact: true },
      { id: "grading", showImpact: true },
    ],
  },
  {
    id: "troubleshooting",
    questions: [{ id: "slow_run" }, { id: "model_unavailable" }],
  },
  {
    id: "corpus_builder",
    adminOnly: true,
    questions: [
      { id: "needs_review" },
      { id: "confidence_not_reported" },
      { id: "retry_vs_rerun", showImpact: true },
      { id: "requeue_record", showImpact: true },
      { id: "publish_visibility" },
      { id: "failed_enrichment" },
    ],
  },
  {
    id: "review",
    adminOnly: true,
    questions: [
      { id: "confirm_value", showImpact: true },
      { id: "evidence", showImpact: true },
      { id: "no_value", showImpact: true },
      { id: "save_all", showImpact: true },
      { id: "second_opinion", showImpact: true },
      { id: "precedents_panel" },
      { id: "research_claims_panel" },
      { id: "accept_record", showImpact: true },
    ],
  },
  {
    id: "memory",
    adminOnly: true,
    questions: [
      { id: "retrieval_policy", showImpact: true },
      { id: "agree_on", showImpact: true },
      { id: "autofill" },
    ],
  },
];

/**
 * Every route that renders an application page has a corresponding guide.
 * Redirect-only compatibility routes are intentionally omitted.
 */
export const HELP_PAGE_GUIDES: HelpPageGuideDefinition[] = [
  {
    id: "dashboard",
    routeName: "home",
    path: "/",
    group: "overview",
    capability: "page.dashboard",
  },
  {
    id: "search",
    routeName: "global",
    path: "/search",
    group: "corpora",
    capability: "page.search",
  },
  {
    id: "research",
    routeName: "rag",
    path: "/rag",
    group: "research",
    showImpact: true,
    capability: "page.research",
  },
  {
    id: "response_library",
    routeName: "faq",
    path: "/faq",
    group: "research",
    showImpact: true,
    capability: "page.faq",
    adminOnly: true,
  },
  { id: "works", routeName: "works", path: "/works", group: "corpora", capability: "page.works" },
  {
    id: "records",
    routeName: "list",
    path: "/records",
    group: "corpora",
    showImpact: true,
    capability: "page.records",
    adminOnly: true,
  },
  {
    id: "record",
    routeName: "record",
    path: "/record",
    group: "corpora",
    showImpact: true,
    capability: "page.record",
  },
  {
    id: "relationships",
    routeName: "relationships",
    path: "/relationships",
    group: "corpora",
    capability: "page.record",
  },
  {
    id: "annotations",
    routeName: "annotations",
    path: "/annotations",
    group: "corpora",
    showImpact: true,
    capability: "page.annotations",
  },
  {
    id: "semantic_map",
    routeName: "semanticmap",
    path: "/semantic-map",
    group: "corpora",
    capability: "page.semantic_map",
  },
  {
    id: "compare",
    routeName: "compare",
    path: "/compare",
    group: "corpora",
    capability: "page.compare",
  },
  {
    id: "corpus_data",
    routeName: "vector",
    path: "/databases",
    group: "corpus_management",
    showImpact: true,
    capability: "page.vector",
  },
  {
    id: "corpus_builder",
    routeName: "corpus-builder",
    path: "/corpus-builder",
    group: "corpus_management",
    showImpact: true,
    capability: "page.pdf",
    adminOnly: true,
  },
  {
    id: "source_explorer",
    routeName: "source-explorer",
    path: "/source-explorer",
    group: "corpus_management",
    capability: "page.pdf",
    adminOnly: true,
  },
  {
    id: "sources",
    routeName: "sources",
    path: "/sources",
    group: "corpus_management",
    showImpact: true,
    capability: "page.pdf",
    adminOnly: true,
  },
  {
    id: "system_overview",
    routeName: "system-data-overview",
    path: "/system-data/overview",
    group: "system",
    capability: "page.response_cache",
    adminOnly: true,
  },
  {
    id: "system_responses",
    routeName: "system-data-responses",
    path: "/system-data/responses",
    group: "system",
    showImpact: true,
    capability: "page.response_cache",
    adminOnly: true,
  },
  {
    id: "system_metadata",
    routeName: "system-data-metadata",
    path: "/system-data/metadata",
    group: "system",
    capability: "page.response_cache",
    adminOnly: true,
  },
  {
    id: "system_databases",
    routeName: "system-data-databases",
    path: "/system-data/databases",
    group: "system",
    capability: "page.response_cache",
    adminOnly: true,
  },
  {
    id: "system_advanced",
    routeName: "system-data-advanced",
    path: "/system-data/advanced",
    group: "system",
    capability: "page.response_cache",
    adminOnly: true,
  },
  {
    id: "pipelines",
    routeName: "pipelines",
    path: "/pipelines",
    group: "ai_automation",
    showImpact: true,
    capability: "page.response_cache",
    adminOnly: true,
  },
  {
    id: "metadata_memory",
    routeName: "metadatamemory",
    path: "/metadata-memory",
    group: "ai_automation",
    showImpact: true,
    capability: "page.response_cache",
    adminOnly: true,
  },
  {
    id: "providers",
    routeName: "providers",
    path: "/providers",
    group: "ai_automation",
    showImpact: true,
    capability: "page.providers",
    adminOnly: true,
  },
  {
    id: "schemas",
    routeName: "schemas",
    path: "/schemas",
    group: "corpus_management",
    showImpact: true,
    capability: "page.schemas",
    adminOnly: true,
  },
  {
    id: "settings",
    routeName: "settings-section",
    path: "/settings/workspace",
    group: "system",
    showImpact: true,
    capability: "page.settings",
  },
  {
    id: "users",
    routeName: "users",
    path: "/users",
    group: "system",
    showImpact: true,
    capability: "page.users",
    adminOnly: true,
  },
  {
    id: "roles",
    routeName: "roles",
    path: "/roles",
    group: "system",
    showImpact: true,
    capability: "page.roles",
    adminOnly: true,
  },
  {
    id: "languages",
    routeName: "languages",
    path: "/languages",
    group: "system",
    showImpact: true,
    capability: "page.languages",
    adminOnly: true,
  },
  {
    id: "operations",
    routeName: "operations",
    path: "/operations",
    group: "system",
    showImpact: true,
    adminOnly: true,
  },
  { id: "help", routeName: "help", path: "/help", group: "support" },
];

export const HELP_GLOSSARY: HelpGlossaryDefinition[] = [
  { id: "llm", category: "ai", aliases: ["large language model", "language model"] },
  { id: "model", category: "ai" },
  { id: "provider", category: "ai", aliases: ["llm provider"] },
  { id: "prompt", category: "ai" },
  { id: "token", category: "ai", aliases: ["tokens"] },
  { id: "context_window", category: "ai", aliases: ["context length"] },
  { id: "temperature", category: "parameters", code: true },
  { id: "top_p", category: "parameters", code: true, aliases: ["nucleus sampling"] },
  { id: "seed", category: "parameters", code: true },
  { id: "embedding", category: "ai", aliases: ["vector embedding"] },
  { id: "embedding_model", category: "ai" },
  { id: "rag", category: "retrieval", aliases: ["retrieval augmented generation"] },
  { id: "retrieval", category: "retrieval" },
  { id: "semantic_search", category: "retrieval", aliases: ["vector search"] },
  { id: "lexical_search", category: "retrieval", aliases: ["bm25", "keyword search"] },
  { id: "hybrid_search", category: "retrieval" },
  { id: "candidate", category: "retrieval" },
  { id: "cosine_similarity", category: "retrieval", aliases: ["similarity", "cosine"] },
  { id: "reranking", category: "retrieval", aliases: ["rerank"] },
  { id: "reranker", category: "retrieval" },
  { id: "cross_encoder", category: "retrieval", aliases: ["cross-encoder", "cross encoding"] },
  { id: "rrf", category: "retrieval", aliases: ["reciprocal rank fusion"] },
  { id: "mmr", category: "retrieval", aliases: ["maximal marginal relevance"] },
  { id: "deduplication", category: "retrieval", aliases: ["dedup"] },
  { id: "query_decomposition", category: "retrieval" },
  { id: "context_packing", category: "retrieval", aliases: ["evidence packaging", "context pack"] },
  { id: "pipeline", category: "retrieval" },
  { id: "pipeline_stage", category: "retrieval", aliases: ["stage"] },
  { id: "fallback", category: "retrieval" },
  { id: "top_k", category: "parameters", code: true, aliases: ["k"] },
  { id: "fetch_k", category: "parameters", code: true },
  { id: "mmr_lambda", category: "parameters", code: true, aliases: ["lambda"] },
  { id: "rrf_k", category: "parameters", code: true },
  { id: "rerank_top_n", category: "parameters", code: true, aliases: ["top n"] },
  { id: "min_similarity", category: "parameters", code: true },
  { id: "evidence_budget", category: "parameters" },
  { id: "max_chars_evidence", category: "parameters", code: true },
  { id: "evidence", category: "provenance" },
  { id: "evidence_binding", category: "provenance" },
  { id: "citation_binding", category: "provenance" },
  { id: "provenance", category: "provenance" },
  { id: "deterministic", category: "provenance" },
  { id: "model_inferred", category: "provenance", aliases: ["llm inferred"] },
  { id: "confidence", category: "provenance" },
  { id: "calibration", category: "provenance" },
  { id: "field_assertion", category: "provenance", aliases: ["fieldassertion"] },
  { id: "source_span", category: "provenance", aliases: ["sourcespan"] },
  { id: "record_revision", category: "provenance", aliases: ["record", "recordrevision"] },
  { id: "authority", category: "provenance" },
  { id: "metadata_precedent", category: "provenance", aliases: ["precedent"] },
  { id: "confirmed_absence", category: "provenance", aliases: ["no value"] },
  { id: "celf", category: "provenance", aliases: ["capta-enriched lexical format"] },
  { id: "chroma", category: "storage" },
  { id: "vector_collection", category: "storage", aliases: ["collection"] },
  { id: "vector_database", category: "storage", aliases: ["vector store"] },
  { id: "derived_index", category: "storage", aliases: ["derived projection"] },
  { id: "response_cache", category: "storage" },
  { id: "metadata_memory", category: "storage" },
  { id: "cached_provenance", category: "storage" },
];

function matchesNeedle(values: Array<string | undefined>, needle: string): boolean {
  return !needle || values.some((value) => value?.toLocaleLowerCase().includes(needle));
}

/** Sections visible to this user, with questions filtered by a free-text query. */
export function visibleHelp(
  isAdmin: boolean,
  query: string,
  t: HelpTranslate,
): Array<{ id: string; title: string; entries: HelpEntry[] }> {
  const needle = query.trim().toLocaleLowerCase();
  return HELP_SECTIONS.filter((section) => isAdmin || !section.adminOnly)
    .map((section) => ({
      id: section.id,
      title: t(`help.section.${section.id}`),
      entries: section.questions
        .map((question) => ({
          id: question.id,
          question: t(`help.q.${question.id}.question`),
          answer: t(`help.q.${question.id}.answer`),
          impact: question.showImpact ? t(`help.q.${question.id}.impact`) : undefined,
        }))
        .filter((entry) => matchesNeedle([entry.question, entry.answer, entry.impact], needle)),
    }))
    .filter((section) => section.entries.length);
}

export function visiblePageGuides(
  isAdmin: boolean,
  can: (capability: string) => boolean,
  query: string,
  t: HelpTranslate,
): HelpPageGuide[] {
  const needle = query.trim().toLocaleLowerCase();
  return HELP_PAGE_GUIDES.filter(
    (guide) =>
      (!guide.adminOnly || isAdmin) && (!guide.capability || isAdmin || can(guide.capability)),
  )
    .map((guide) => ({
      ...guide,
      title: t(`help.page.${guide.id}.title`),
      summary: t(`help.page.${guide.id}.summary`),
      tasks: t(`help.page.${guide.id}.tasks`),
      impact: guide.showImpact ? t(`help.page.${guide.id}.impact`) : undefined,
    }))
    .filter((guide) =>
      matchesNeedle(
        [guide.title, guide.summary, guide.tasks, guide.impact, t(`help.group.${guide.group}`)],
        needle,
      ),
    );
}

export function visibleGlossary(
  query: string,
  category: HelpGlossaryCategory,
  t: HelpTranslate,
): HelpGlossaryEntry[] {
  const needle = query.trim().toLocaleLowerCase();
  return HELP_GLOSSARY.filter((entry) => category === "all" || entry.category === category)
    .map((entry) => ({
      ...entry,
      term: t(`help.glossary.${entry.id}.term`),
      definition: t(`help.glossary.${entry.id}.definition`),
      practical: t(`help.glossary.${entry.id}.practical`),
    }))
    .filter((entry) =>
      matchesNeedle(
        [
          entry.term,
          entry.definition,
          entry.practical,
          t(`help.glossary.category.${entry.category}`),
          ...(entry.aliases ?? []),
        ],
        needle,
      ),
    )
    .sort((a, b) => a.term.localeCompare(b.term));
}
