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
  | "core"
  | "ai"
  | "retrieval"
  | "parameters"
  | "provenance"
  | "storage"
  | "operations";

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

export interface HelpStarterDefinition {
  id: string;
  path: string;
  icon: string;
  adminOnly?: boolean;
  capability?: string;
}

export interface HelpStarter extends HelpStarterDefinition {
  title: string;
  description: string;
}

export const HELP_STARTERS: HelpStarterDefinition[] = [
  { id: "find_passage", path: "/search", icon: "search", capability: "page.search" },
  { id: "ask_research", path: "/rag", icon: "spark", capability: "page.research" },
  { id: "browse_works", path: "/works", icon: "books", capability: "page.works" },
  { id: "learn_terms", path: "/help#help-glossary", icon: "help" },
  {
    id: "build_corpus",
    path: "/corpus-builder",
    icon: "upload",
    capability: "page.pdf",
    adminOnly: true,
  },
  {
    id: "review_records",
    path: "/records",
    icon: "record",
    capability: "page.records",
    adminOnly: true,
  },
];

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
      { id: "memory_vs_evidence" },
      { id: "no_citations" },
      { id: "rerun_answer" },
      { id: "why_results_change" },
      { id: "choose_model" },
      { id: "cached_responses", showImpact: true },
      { id: "cached_provenance", showImpact: true },
      { id: "validate_claims", showImpact: true },
      { id: "grading", showImpact: true },
    ],
  },
  {
    id: "access",
    questions: [
      { id: "missing_page" },
      { id: "browser_vs_server" },
      { id: "automatic_updates" },
    ],
  },
  {
    id: "troubleshooting",
    questions: [{ id: "slow_run" }, { id: "model_unavailable" }, { id: "queued_run" }],
  },
  {
    id: "sources_ingestion",
    adminOnly: true,
    questions: [
      { id: "supported_sources" },
      { id: "media_specific_controls" },
      { id: "extraction_provenance" },
      { id: "safe_ingestion" },
    ],
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
      { id: "publish_suggestions", showImpact: true },
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
      { id: "memory_vs_examples" },
    ],
  },
  {
    id: "pipelines_operations",
    adminOnly: true,
    questions: [
      { id: "pipeline_assignment", showImpact: true },
      { id: "pipeline_trace" },
      { id: "cancel_operation", showImpact: true },
      { id: "interrupted_operation" },
    ],
  },
  {
    id: "data_publishing",
    adminOnly: true,
    questions: [
      { id: "system_data" },
      { id: "data_retention", showImpact: true },
      { id: "backup_restore", showImpact: true },
      { id: "static_site", showImpact: true },
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
    path: "/settings/overview",
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
  { id: "corpus", category: "core" },
  { id: "work", category: "core" },
  { id: "record", category: "core" },
  { id: "review_state", category: "core", aliases: ["needs review", "accepted", "rejected"] },
  { id: "speaker", category: "core" },
  { id: "position_holder", category: "core", aliases: ["position holder"] },
  { id: "stance", category: "core" },
  { id: "proposition", category: "core" },
  { id: "claim", category: "core", aliases: ["generated claim"] },
  { id: "support_binding", category: "core", aliases: ["supportbinding"] },
  { id: "evidence_packet", category: "core", aliases: ["evidencepacket"] },
  { id: "llm", category: "ai", aliases: ["large language model", "language model"] },
  { id: "model", category: "ai" },
  { id: "provider", category: "ai", aliases: ["llm provider"] },
  { id: "prompt", category: "ai" },
  { id: "token", category: "ai", aliases: ["tokens"] },
  { id: "context_window", category: "ai", aliases: ["context length"] },
  { id: "temperature", category: "parameters", code: true },
  { id: "top_p", category: "parameters", code: true, aliases: ["nucleus sampling"] },
  { id: "seed", category: "parameters", code: true },
  { id: "sampling_top_k", category: "parameters", code: true, aliases: ["sampling top_k"] },
  { id: "num_ctx", category: "parameters", code: true, aliases: ["context tokens"] },
  { id: "max_output_tokens", category: "parameters", code: true, aliases: ["output tokens"] },
  { id: "keep_alive", category: "parameters", code: true },
  { id: "embedding", category: "ai", aliases: ["vector embedding"] },
  { id: "embedding_model", category: "ai" },
  { id: "structured_output", category: "ai", aliases: ["structured json", "json output"] },
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
  { id: "canonical_state", category: "provenance", aliases: ["authoritative state"] },
  { id: "derived_state", category: "provenance", aliases: ["derived data", "projection"] },
  { id: "source_asset", category: "provenance", aliases: ["source file"] },
  { id: "extraction_provenance", category: "provenance", aliases: ["extractor provenance"] },
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
  { id: "blind_second_opinion", category: "provenance", aliases: ["blind review"] },
  { id: "calibrated_autofill", category: "provenance", aliases: ["autofill"] },
  { id: "celf", category: "provenance", aliases: ["capta-enriched lexical format"] },
  { id: "chroma", category: "storage" },
  { id: "vector_collection", category: "storage", aliases: ["collection"] },
  { id: "vector_database", category: "storage", aliases: ["vector store"] },
  { id: "derived_index", category: "storage", aliases: ["derived projection"] },
  { id: "response_cache", category: "storage" },
  { id: "response_library", category: "storage" },
  { id: "metadata_example", category: "storage", aliases: ["metadata examples"] },
  { id: "metadata_memory", category: "storage" },
  { id: "response_memory", category: "storage", aliases: ["cached responses"] },
  { id: "claim_memory", category: "storage", aliases: ["cached provenance"] },
  { id: "cached_provenance", category: "storage" },
  { id: "browser_workspace", category: "storage", aliases: ["indexeddb", "browser local"] },
  { id: "system_data", category: "storage" },
  { id: "operation", category: "operations", aliases: ["background operation"] },
  { id: "job", category: "operations", aliases: ["background job"] },
  { id: "pipeline_trace", category: "operations", aliases: ["execution trace"] },
  { id: "benchmark", category: "operations" },
  { id: "document_intelligence", category: "operations", aliases: ["nlp annotations"] },
  { id: "semantic_content_graph", category: "operations", aliases: ["semantic graph"] },
  { id: "research_object_graph", category: "operations", aliases: ["celf research object graph"] },
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

/** Task-first Help Center entry points visible to the current role. */
export function visibleStarters(
  isAdmin: boolean,
  can: (capability: string) => boolean,
  t: HelpTranslate,
): HelpStarter[] {
  return HELP_STARTERS.filter(
    (starter) =>
      (!starter.adminOnly || isAdmin) &&
      (!starter.capability || isAdmin || can(starter.capability)),
  ).map((starter) => ({
    ...starter,
    title: t(`help.starter.${starter.id}.title`),
    description: t(`help.starter.${starter.id}.description`),
  }));
}
