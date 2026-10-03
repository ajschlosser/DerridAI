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

import type { Page } from "@playwright/test";

// A stand-in for the API, so the real app (shell, router, runtime and Vue views) can be rendered in
// a browser without a backend. Requests under /api/ are answered here; everything else is served by
// the preview server. A scenario overrides only the endpoints it cares about.

export type Role = "admin" | "researcher";
type Responder = unknown | ((url: URL, method: string) => unknown);
/** Keyed by "/api/path" (any method) or "METHOD /api/path". */
export type Fixtures = Record<string, Responder>;

export const LANGUAGES = [
  { code: "en-US", name: "English (United States)", flag: "us", content_policy_ready: true },
  { code: "fr-CA", name: "Français (Canada)", flag: "ca", content_policy_ready: true },
  { code: "de-DE", name: "Deutsch", flag: "de", content_policy_ready: false },
];

const RESEARCHER_CAPABILITIES = [
  "page.record",
  "page.dashboard",
  "page.search",
  "annotations.read",
  "annotations.write",
  "evidence.select",
];

export const STORE_RECORDS = [
  {
    _chroma_id: "r1",
    record_id: "derrida-cosmopoli-00011",
    work: "On Cosmopolitanism and Forgiveness",
    document_author: "Jacques Derrida",
    page_start: 5,
    page_end: 5,
    text: "I regret not having been present at the inauguration of this solemn meeting, but permit me, by way of saluting those here present, to evoke at least a vague outline of this new charter of hospitality.",
    speaker: "Derrida",
    position_holder: "Derrida",
    discourse_role: "assertion",
    stance: "affirm",
    topics: ["hospitality", "cities of refuge"],
    concepts: ["hospitality"],
  },
  {
    _chroma_id: "r2",
    record_id: "derrida-cosmopoli-00012",
    work: "On Cosmopolitanism and Forgiveness",
    document_author: "Jacques Derrida",
    page_start: 6,
    page_end: 6,
    text: "What then would such a concept be?",
  },
  {
    _chroma_id: "r3",
    record_id: "derrida-cosmopoli-00013",
    work: "On Cosmopolitanism and Forgiveness",
    document_author: "Jacques Derrida",
    page_start: 6,
    page_end: 8,
    text: "How might it be adapted to the pressing urgencies which summon and overwhelm us?",
  },
];

const GRADE = {
  overall: 8,
  summary: "Strong source binding with one attribution risk.",
  analysis:
    "The response is useful and well grounded overall, but one interpretive transition should be qualified.",
  categories: {
    query_relevance: { score: 9, analysis: "Directly answers the question." },
    source_binding: { score: 9, analysis: "Claims are tied to supplied evidence." },
    coverage: { score: 7, analysis: "A secondary thread is omitted." },
  },
  strengths: ["Clear source binding"],
  weaknesses: ["One compressed transition"],
  unsupported_or_risky_claims: ["Qualify the attribution in paragraph three"],
};

export const FAQ_RECORDS = [
  {
    record_id: "faq-1",
    question: "How does Derrida distinguish responsibility from programmable rule-following?",
    text: "Responsibility begins where a decision cannot be reduced to a rule or program (Derrida 1999: 20–21).\n\nA responsible decision must still answer to inherited norms while passing through an irreducible ordeal of undecidability (Derrida 1999: 24).",
    provider: "Ollama",
    model: "qwen3:14b",
    created_at: "2026-09-01T12:00:00Z",
    elapsed_seconds: 12.4,
    evidence_count: 2,
    evidence: [
      {
        evidence_id: "E1",
        inline_citation: "(Derrida 1999: 20–21)",
        full_citation: "Derrida, Jacques. The Gift of Death.",
        collection: "derrida-en",
        rerank_score: 0.931,
        record: {
          record_id: "gift-020",
          work: "The Gift of Death",
          page_start: 20,
          page_end: 21,
          speaker: "Derrida",
          text: "The responsible decision is not a calculable one.",
        },
      },
      {
        evidence_id: "E2",
        inline_citation: "(Derrida 1999: 24)",
        full_citation: "Derrida, Jacques. The Gift of Death.",
        collection: "derrida-en",
        rerank_score: 0.902,
        record: {
          record_id: "gift-024",
          work: "The Gift of Death",
          page_start: 24,
          speaker: "Derrida",
          text: "Undecidability is the ordeal through which a decision passes.",
        },
      },
    ],
    grade: GRADE,
    warnings: [],
  },
  {
    record_id: "faq-2",
    question: "What is the difference between conditional and unconditional hospitality?",
    text: "Unconditional hospitality exceeds the law; conditional hospitality is what makes welcome possible (Derrida 2000: 77).",
    provider: "Ollama",
    model: "qwen3:14b",
    created_at: "2026-09-02T09:30:00Z",
    evidence_count: 0,
    evidence: [],
    warnings: ["No evidence was selected for this answer."],
  },
  {
    record_id: "faq-3",
    question: "Why does Derrida return to the figure of the city of refuge?",
    text: "The city of refuge stages the tension between sovereignty and welcome.",
    provider: "OpenAI-compatible",
    model: "gpt-oss:20b",
    created_at: "2026-09-03T15:45:00Z",
    evidence_count: 0,
    evidence: [],
  },
];

// A corpus build waiting for review, with records in every queue state, for the Corpus Builder.
const PROSE = [
  "The concept of hospitality is never simply given; it is inherited through a tradition that already divides the welcome into a law and its exceptions.",
  "To ask who is the guest is already to condition the welcome, and yet without that question no one could be received at all.",
  "The city that shelters the stranger must decide, at each arrival, what it owes to the one it cannot yet name.",
  "What returns in these pages is a demand that exceeds every particular policy while remaining impossible to practise outside one.",
  "A duty of hospitality that is only dutiful would already have failed the visitor, who comes not as a case but as a face.",
  "We should therefore hesitate before treating the refuge as a solution: it is a place where the problem is kept open.",
];
const STATES = [
  "metadata",
  "metadata",
  "topology",
  "ready",
  "accepted",
  "ready",
  "metadata",
  "rejected",
];
export const CORPUS_BUILD_ID = "build-0001";
export const CORPUS_RECORDS = Array.from({ length: 60 }, (_, i) => {
  const n = i + 12;
  const state = STATES[i % STATES.length];
  const body = Array.from({ length: 9 }, (_, k) => PROSE[(i + k) % PROSE.length]).join(" ");
  const unresolved = state === "metadata" ? ["target", "stance", "proposition_status"] : [];
  return {
    record_id: `derrida-jacques-on-cosmopoli-${String(n).padStart(5, "0")}`,
    text: body,
    text_length: body.length,
    page_start: 5 + Math.floor(i / 3),
    page_end: 5 + Math.floor(i / 3) + (i % 4 === 0 ? 2 : 0),
    source_block_ids: [`b${n}a`, `b${n}b`],
    source_spans: [{ block_id: `b${n}a`, page: 5 + Math.floor(i / 3) }],
    metadata_field_status: Object.fromEntries(
      unresolved.map((f, k) => [
        f,
        {
          status: "model_inferred",
          method: "llm",
          confidence: [0.95, 0.85, 0.7][k],
          reason: "Suggested from the surrounding argument; confirm it against the text.",
        },
      ]),
    ),
    metadata_incomplete_fields: unresolved,
    metadata_review_fields: unresolved,
    acceptance_blocking_fields: unresolved,
    metadata_complete: unresolved.length === 0,
    review_state: state,
    review_disposition:
      state === "accepted" ? "accepted" : state === "rejected" ? "rejected" : "pending",
    accepted: state === "accepted",
    rejected: state === "rejected",
    needs_review: state === "metadata" || state === "topology",
    can_accept: unresolved.length === 0,
    review_issue_codes: state === "topology" ? ["boundary_continuation"] : [],
    review_reason:
      state === "topology"
        ? "Possible sentence/quotation continuation across this record boundary."
        : "Pending human review.",
    record_revision: 1,
    topology_index: i,
    topology_count: 60,
    pdf_pages: [5 + Math.floor(i / 3)],
    speaker: "Derrida",
    discourse_role: "analysis",
  };
});
export const CORPUS_BUILD = {
  build_id: CORPUS_BUILD_ID,
  asset_id: "asset-1",
  source_filename: "derrida-on-cosmopolitanism.pdf",
  source_sha256: "0".repeat(64),
  status: "awaiting_review",
  stage: "review",
  progress: 0.9,
  created_at: "2026-09-18T12:00:00Z",
  record_count: 60,
  needs_review_count: 30,
  accepted_count: 8,
  rejected_count: 8,
  profile_id: "derrida-v11",
  provider: "ollama",
  model: "qwen3:14b",
  review_queue_counts: {
    all: 60,
    ready: 15,
    issues: 30,
    metadata: 23,
    topology: 8,
    source: 0,
    accepted: 8,
    rejected: 8,
    pending: 44,
  },
  manifest: { title: "On Cosmopolitanism and Forgiveness", document_author: "Jacques Derrida" },
  manifest_confirmed_at: "2026-09-18T12:05:00Z",
  validation: { valid: true, source_valid: true, metadata_valid: false, coverage: 1 },
  metadata_issue_summary: {
    records_incomplete: 23,
    fields_unresolved: 69,
    auto_retry_fields: 0,
    human_review_fields: 69,
  },
  publication_readiness: {
    can_publish: false,
    next_action: "review",
    records_total: 60,
    records_reviewed: 16,
    records_accepted: 8,
    records_rejected: 8,
    records_pending: 44,
    blockers: [],
  },
  metadata_total: 60,
  metadata_completed: 60,
};

function defaults(url: URL, method: string, role: Role): unknown {
  const path = url.pathname;
  const user = {
    id: 1,
    username: "admin",
    role,
    role_name: role === "admin" ? "Administrator" : "Researcher",
    active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    login_count: 1,
    capabilities: role === "admin" ? [] : RESEARCHER_CAPABILITIES,
  };
  if (path === "/api/auth/status") return { bootstrap_required: false, authenticated: true, user };
  if (path === "/api/auth/users") return { users: [user] };
  if (path === "/api/auth/roles") {
    const capabilities = [
      {
        id: "page.dashboard",
        category: "Pages",
        label: "Dashboard",
        description: "Open the dashboard.",
        configurable: true,
      },
      {
        id: "page.research",
        category: "Pages",
        label: "Research",
        description: "Open Research.",
        configurable: true,
      },
      {
        id: "corpus.read",
        category: "Corpus",
        label: "Read corpus",
        description: "Read corpus records.",
        configurable: true,
      },
      {
        id: "rag.run",
        category: "Research",
        label: "Run RAG",
        description: "Start RAG jobs.",
        configurable: true,
      },
      {
        id: "users.manage",
        category: "Administration",
        label: "Manage users",
        description: "Administrator-only.",
        configurable: false,
      },
    ];
    return {
      capabilities,
      roles: [
        {
          id: "admin",
          name: "Administrator",
          description: "Full application access.",
          locked: true,
          builtin: true,
          permissions: ["*"],
        },
        {
          id: "researcher",
          name: "Researcher",
          description: "Default non-admin research role.",
          locked: false,
          builtin: true,
          permissions: ["page.dashboard", "page.research", "corpus.read", "rag.run"],
        },
      ],
    };
  }
  if (path === "/api/i18n/languages") return { languages: LANGUAGES };
  if (path === "/api/i18n/content-policy")
    return { ready: true, locales: ["en-US", "fr-CA"], blocked_term_hashes: [], contextual: [] };
  const policy = path.match(/^\/api\/i18n\/languages\/([^/]+)\/content-policy$/);
  if (policy)
    return {
      code: policy[1],
      status: "ready",
      blocked_terms: ["exampleterm"],
      contextual_terms: [],
      source: "generated",
      provider: "ollama",
      model: "gemma4:12b",
      generated_at: "2026-09-01T00:00:00Z",
    };
  const language = path.match(/^\/api\/i18n\/languages\/([^/]+)$/);
  if (language)
    return { ...(LANGUAGES.find((l) => l.code === language[1]) ?? LANGUAGES[0]), dictionary: {} };
  if (path === "/api/jobs") return { jobs: [] };
  if (path === "/api/system/researcher-providers")
    return {
      profiles: [{ id: "primary", name: "Local Ollama", type: "ollama", model: "gemma4:12b" }],
    };
  if (path === "/api/stores")
    return {
      stores: [
        {
          name: "derrida_primary",
          kind: "records",
          count: STORE_RECORDS.length,
          embedding_model: "bge-m3:latest",
        },
      ],
    };
  if (path === "/api/stores/derrida_primary/records")
    return { count: STORE_RECORDS.length, records: STORE_RECORDS };
  if (path === "/api/annotations") return { annotations: [] };
  if (path === "/api/system/data-retention")
    return {
      policy: { default: { mode: "keep", value: null }, stores: {} },
      evaluated_at: "2026-03-01T12:00:00Z",
      applied: false,
      stores: [],
    };
  if (path === "/api/system/data")
    return {
      databases: [
        {
          name: "system",
          backend: "sqlite",
          path: "system.db",
          size_bytes: 0,
          tables: [],
        },
        {
          name: "auth",
          backend: "sqlite",
          path: "auth.db",
          size_bytes: 0,
          tables: [],
        },
      ],
    };
  if (path === "/api/system/data/metadata-exemplars")
    return {
      exists: false,
      count: 0,
      limit: 25,
      offset: 0,
      rows: [],
      facets: { fields: [], kinds: [], languages: [], scopes: [], schemas: [] },
    };
  if (path === "/api/system/data/vector-stores") return { stores: [] };
  if (path === "/api/response-cache/records")
    return { records: [], count: 0, total: 0, limit: 50, offset: 0, exists: true };
  if (path === "/api/pdf/corpus-profiles")
    return { items: [{ id: "derrida-v11", name: "DerridAI corpus profile", version: 11 }] };
  if (path === "/api/pdf/assets")
    return {
      items: [
        {
          asset_id: "asset-1",
          sha256: "0".repeat(64),
          filename: "derrida-on-cosmopolitanism.pdf",
          created_at: "2026-09-18T11:00:00Z",
          page_count: 120,
          block_count: 1400,
          ocr_pages: 0,
          warnings: [],
          metadata: {},
          pages: [],
        },
      ],
    };
  if (path === "/api/pdf/corpus-builds")
    return { items: [CORPUS_BUILD], total: 1, offset: 0, limit: 50 };
  if (path === `/api/pdf/corpus-builds/${CORPUS_BUILD_ID}`) return CORPUS_BUILD;
  if (path === `/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records`) {
    const offset = Number(url.searchParams.get("offset") || 0);
    const limit = Number(url.searchParams.get("limit") || 50);
    const queue = url.searchParams.get("review_queue") || "";
    const rows = CORPUS_RECORDS.filter(
      (r) =>
        !queue ||
        queue === "all" ||
        (queue === "issues"
          ? r.needs_review
          : queue === "ready"
            ? r.review_state === "ready"
            : r.review_state === queue),
    );
    return { items: rows.slice(offset, offset + limit), total: rows.length, offset, limit };
  }
  if (path === "/api/corpus/source-providers")
    return {
      items: [
        {
          provider: "gutenberg",
          catalogue_ready: true,
          catalogue_refreshed_at: "2026-09-26T12:00:00Z",
          local_collection_ready: true,
        },
        {
          provider: "wikisource",
          projects: [
            { code: "en", name: "English" },
            { code: "fr", name: "French" },
            { code: "de", name: "German" },
          ],
          projects_authoritative: true,
        },
      ],
    };
  if (path === "/api/corpus/authors/search")
    return {
      items: [
        {
          wikidata_qid: "Q130631",
          label: "Jacques Derrida",
          description: "French philosopher (1930–2004)",
          aliases: ["Jackie Derrida"],
          birth_year: 1930,
          death_year: 2004,
          wikisource_sitelinks: { fr: "Jacques Derrida" },
        },
      ],
    };
  if (path === "/api/corpus/captures" && method === "GET") return { items: [] };
  if (path === "/api/corpus/sources")
    return {
      items: [],
      total: 0,
      offset: Number(url.searchParams.get("offset") || 0),
      limit: Number(url.searchParams.get("limit") || 25),
      facets: {},
    };
  if (path === "/api/gutenberg/status")
    return {
      ready: true,
      search_ready: true,
      catalogue: { status: "ready", item_count: 74213 },
      archive: { status: "ready", bytes_done: 1, total_bytes: 1 },
    };
  if (path === "/api/pdf/gutenberg/search")
    return {
      items: [
        {
          etext_id: 46333,
          title: "The Social Contract & Discourses",
          author: "Jean-Jacques Rousseau",
          language: "en",
        },
        {
          etext_id: 3913,
          title: "The Confessions of Jean Jacques Rousseau — Complete",
          author: "Jean-Jacques Rousseau",
          language: "en",
        },
        {
          etext_id: 5427,
          title: "Émile ou de l'éducation",
          author: "Jean-Jacques Rousseau",
          language: "fr",
        },
      ],
    };
  if (path === "/api/pdf/wikisource/search") {
    const host = `https://${url.searchParams.get("language") || "en"}.wikisource.org/wiki/`;
    const hit = (title: string, snippet: string, words: number) => ({
      source: "wikisource",
      title,
      page_id: title.length,
      snippet,
      word_count: words,
      url: host + encodeURIComponent(title.replaceAll(" ", "_")),
    });
    return {
      items: [
        hit(
          "Du contrat social/Édition 1762/Livre I",
          "L’homme est né libre, et partout il est dans les fers.",
          4120,
        ),
        hit(
          "Du contrat social/Édition 1762/Livre II",
          "La première et la plus importante conséquence des principes…",
          6023,
        ),
        hit(
          "Discours sur l’origine et les fondements de l’inégalité parmi les hommes",
          "C’est de l’homme que j’ai à parler…",
          31877,
        ),
        hit(
          "Les Confessions (Rousseau)/Livre I",
          "Je forme une entreprise qui n’eut jamais d’exemple…",
          15210,
        ),
      ],
    };
  }
  const context = path.match(
    new RegExp(`^/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records/([^/]+)/context$`),
  );
  if (context) {
    const index = CORPUS_RECORDS.findIndex((r) => r.record_id === decodeURIComponent(context[1]));
    const item = (r: (typeof CORPUS_RECORDS)[number]) => ({
      record_id: r.record_id,
      text: r.text,
      text_length: r.text.length,
      page_start: null,
      page_end: null,
    });
    return {
      record_id: decodeURIComponent(context[1]),
      before: index > 0 ? CORPUS_RECORDS.slice(Math.max(0, index - 2), index).map(item) : [],
      after: index >= 0 ? CORPUS_RECORDS.slice(index + 1, index + 3).map(item) : [],
      truncated: false,
    };
  }
  if (/^\/api\/pdf\/assets\/[^/]+\/blocks$/.test(path)) return { items: [], total: 0 };
  return {};
}

/** A record shaped like one REST response item, read loosely (fixtures may override the shape). */
type LooseRecord = Record<string, any>;

/** The REST default (or its fixture override) for one synthetic GET, keyed the same way as a real request. */
function restFallback(
  path: string,
  fixtures: Fixtures,
  role: Role,
  searchParams: Record<string, string> = {},
): LooseRecord {
  const restUrl = new URL(path, "http://mock.local");
  for (const [key, value] of Object.entries(searchParams)) restUrl.searchParams.set(key, value);
  const override = fixtures[`GET ${path}`] ?? fixtures[path];
  const body = override === undefined ? defaults(restUrl, "GET", role) : override;
  return (typeof body === "function" ? body(restUrl, "GET") : body) as LooseRecord;
}

/** A review-queue row, the same fields the server derives from a Record (CorpusQueueRow.from_presented_record). */
function queueRow(record: LooseRecord): LooseRecord {
  const text = String(record.text || "");
  return {
    record_id: record.record_id,
    record_revision: record.record_revision ?? null,
    state_version: record.state_version ?? record.record_revision ?? 1,
    page_start: record.page_start != null ? String(record.page_start) : null,
    page_end: record.page_end != null ? String(record.page_end) : null,
    text_length: Number(record.text_length ?? text.length),
    text_preview: text.length > 90 ? `${text.slice(0, 90)}…` : text,
    review_state: record.review_state || "ready",
    review_issue_codes: record.review_issue_codes ?? [],
    review_disposition: record.review_disposition || (record.accepted ? "accepted" : "pending"),
    metadata_llm_processed: Boolean(record.metadata_enrichment_finished),
    needs_review: Boolean(record.needs_review),
    source_quality_issues: Boolean(
      record.source_quality_issues && record.source_quality_issues.length,
    ),
    metadata_complete: Boolean(record.metadata_complete),
  };
}

function vectorRow(record: LooseRecord): LooseRecord {
  return {
    chroma_id: String(record._chroma_id || record.record_id || ""),
    record_id: record.record_id ?? null,
    work: record.work ?? null,
    page_start: record.page_start != null ? String(record.page_start) : null,
    page_end: record.page_end != null ? String(record.page_end) : null,
    text_summarized: false,
    text_preview: String(record.text || "").slice(0, 90),
  };
}

/** The full (unpaginated, unfiltered) Corpus Builder record list, for the record-id-scoped reads. */
function corpusRecordsAll(buildId: string, fixtures: Fixtures, role: Role): LooseRecord[] {
  const page = restFallback(`/api/pdf/corpus-builds/${buildId}/records`, fixtures, role, {
    offset: "0",
    limit: "1000",
  });
  return Array.isArray(page.items) ? page.items : [];
}

/**
 * Answers for the read-only GraphQL façade. Corpus Builder and Vector Store reads are derived from
 * the same REST fixtures/defaults their REST predecessors used, so a scenario that overrides one
 * REST endpoint (or none at all) gets a consistent answer on both transports without duplicating
 * fixture data. `CelfModel` and `SimilarValidatedClaims` have no REST predecessor and stay static.
 */
export function graphqlDefaults(
  operationName: string,
  variables: LooseRecord,
  fixtures: Fixtures,
  role: Role,
): unknown {
  if (operationName === "CelfModel")
    return { data: { celf_model: { specification_version: "1.0", nodes: [], edges: [] } } };
  if (operationName === "SimilarValidatedClaims")
    return { data: { generated_claim: { claim_id: "", similar_validated_claims: [] } } };

  if (operationName === "CorpusReviewQueue") {
    const buildId = String(variables.build_id || "");
    const queue = String(variables.review_queue || "all");
    let offset = Number(variables.offset || 0);
    const limit = Number(variables.limit || 50);
    const build = restFallback(`/api/pdf/corpus-builds/${buildId}`, fixtures, role);
    const topologyGeneration = Number(build.review_queue_topology_generation ?? 1);
    const dataGeneration = Number(build.review_queue_data_generation ?? 1);
    const context = JSON.stringify([
      buildId,
      role,
      queue,
      variables.query || "",
      variables.needs_review ?? null,
      variables.disposition ?? null,
      variables.metadata_incomplete ?? null,
      variables.source_problem ?? null,
    ]);
    const filters = {
      ...(queue && queue !== "all" ? { review_queue: queue } : {}),
      ...(variables.query ? { query: String(variables.query) } : {}),
    };
    const position = (record: LooseRecord) =>
      Number(
        record.topology_index ??
          corpusRecordsAll(buildId, fixtures, role).findIndex(
            (item) => item.record_id === record.record_id,
          ),
      );
    if (variables.cursor) {
      let anchor: { context: string; topologyGeneration: number; position: number };
      try {
        anchor = JSON.parse(Buffer.from(String(variables.cursor), "base64url").toString());
        if (anchor.context !== context) throw new Error("Cursor context changed");
      } catch {
        return {
          data: null,
          errors: [
            { message: "Invalid queue cursor context", extensions: { code: "BAD_REQUEST" } },
          ],
        };
      }
      if (anchor.topologyGeneration !== topologyGeneration)
        return {
          data: null,
          errors: [
            { message: "Queue topology changed", extensions: { code: "STALE_QUEUE_CURSOR" } },
          ],
        };
      const filtered = restFallback(`/api/pdf/corpus-builds/${buildId}/records`, fixtures, role, {
        offset: "0",
        limit: "1000",
        ...filters,
      }).items as LooseRecord[];
      if (variables.direction === "backward") {
        const before = filtered.filter((record) => position(record) < anchor.position).length;
        offset = Math.max(0, before - limit);
      } else {
        const after = filtered.findIndex((record) => position(record) > anchor.position);
        offset = after < 0 ? filtered.length : after;
      }
    }
    const page = restFallback(`/api/pdf/corpus-builds/${buildId}/records`, fixtures, role, {
      offset: String(offset),
      limit: String(limit),
      ...filters,
    });
    const items: LooseRecord[] = Array.isArray(page.items) ? page.items : [];
    const total = Number(page.total ?? items.length);
    const cursor = (record: LooseRecord) =>
      Buffer.from(
        JSON.stringify({ context, topologyGeneration, position: position(record) }),
      ).toString("base64url");
    const queue_counts = {
      all: 0,
      ready: 0,
      preparing: 0,
      issues: 0,
      metadata: 0,
      topology: 0,
      source: 0,
      accepted: 0,
      rejected: 0,
      pending: 0,
      ...(build.review_queue_counts || {}),
    };
    return {
      data: {
        corpus_build: {
          build_id: buildId,
          review_queue: {
            items: items.map(queueRow),
            total,
            offset,
            limit,
            queue_counts,
            topology_count: Number(
              build.record_count ?? corpusRecordsAll(buildId, fixtures, role).length,
            ),
            data_generation: dataGeneration,
            topology_generation: topologyGeneration,
            next_cursor:
              offset + items.length < total && items.length ? cursor(items.at(-1)!) : null,
            previous_cursor: offset > 0 && items.length ? cursor(items[0]) : null,
            has_next_page: offset + items.length < total,
            has_previous_page: offset > 0,
          },
        },
      },
    };
  }

  if (operationName === "CorpusQueueRows" || operationName === "CorpusReviewRecords") {
    const buildId = String(variables.build_id || "");
    const wanted = new Set((variables.record_ids || []).map(String));
    const items = corpusRecordsAll(buildId, fixtures, role).filter((record) =>
      wanted.has(String(record.record_id)),
    );
    return operationName === "CorpusQueueRows"
      ? { data: { corpus_build: { rows: items.map(queueRow) } } }
      : {
          data: {
            corpus_build: {
              records: items.map((record) => ({
                record_id: record.record_id,
                record_revision: record.record_revision ?? null,
                review_document: record,
              })),
            },
          },
        };
  }

  if (operationName === "CorpusQueueTexts") {
    const buildId = String(variables.build_id || "");
    const wanted = new Set((variables.record_ids || []).map(String));
    const items = corpusRecordsAll(buildId, fixtures, role).filter((record) =>
      wanted.has(String(record.record_id)),
    );
    return {
      data: {
        corpus_build: {
          records: items.map((record) => ({ record_id: record.record_id, text: record.text })),
        },
      },
    };
  }

  if (operationName === "CorpusMetadataFacets")
    return { data: { corpus_build: { metadata_facets: [] } } };

  if (operationName === "VectorStoreBrowse") {
    const name = String(variables.name || "");
    const store = restFallback(`/api/stores/${name}/records`, fixtures, role);
    const records: LooseRecord[] = Array.isArray(store.records) ? store.records : [];
    const workStats = new Map<string, { count: number; total_words: number }>();
    for (const record of records) {
      const work = String(record.work || "");
      if (!work) continue;
      const words = String(record.text || "")
        .split(/\s+/)
        .filter(Boolean).length;
      const stat = workStats.get(work) || { count: 0, total_words: 0 };
      stat.count += 1;
      stat.total_words += words;
      workStats.set(work, stat);
    }
    const works = [...workStats.entries()].map(([work, stat]) => ({
      work,
      count: stat.count,
      total_words: stat.total_words,
      average_record_length: stat.count ? Math.round(stat.total_words / stat.count) : 0,
    }));
    let recordsField: LooseRecord | null = null;
    if (variables.includeRecords) {
      const filtered = variables.work ? records.filter((r) => r.work === variables.work) : records;
      const offset = Number(variables.offset || 0);
      const limit = Number(variables.limit || 50);
      const page = filtered.slice(offset, offset + limit);
      recordsField = {
        items: page.map(vectorRow),
        count: filtered.length,
        offset,
        limit,
      };
    }
    return { data: { vector_store: { name, works, records: recordsField } } };
  }

  if (operationName === "StoredRecordTrace") {
    const name = String(variables.store || "");
    const store = restFallback(`/api/stores/${name}/records`, fixtures, role);
    const records: LooseRecord[] = Array.isArray(store.records) ? store.records : [];
    const record = records.find(
      (item) => String(item._chroma_id || "") === String(variables.chroma_id || ""),
    );
    if (!record) return { data: { vector_store: { record: null } } };
    return {
      data: {
        vector_store: {
          record: {
            chroma_id: String(record._chroma_id || ""),
            record_id: record.record_id ?? null,
            materialization: "vector_projection",
            document: record,
            graph: {
              specification_version: "1.0",
              root_id: String(record._chroma_id || ""),
              hidden_assertion_count: 0,
              record_state_origin: "vector_projection",
              nodes: [],
              edges: [],
            },
          },
        },
      },
    };
  }

  return { data: null, errors: [{ message: `No e2e fixture for ${operationName}` }] };
}

/**
 * A minimal realtime server: it accepts the socket, reports ready, acknowledges subscriptions and
 * answers pings. It never pushes events, so pages rely on the REST resync that follows connecting.
 * `refused` closes the socket the way a deployment with realtime disabled would.
 */
async function mockRealtime(page: Page, mode: "live" | "refused"): Promise<void> {
  await page.routeWebSocket(
    (url) => url.pathname === "/api/ws/events",
    (ws) => {
      if (mode === "refused") {
        void ws.close({ code: 4403, reason: "realtime disabled" });
        return;
      }
      const topics = new Set<string>();
      const frame = (type: string, payload: Record<string, unknown>) =>
        ws.send(JSON.stringify({ type, timestamp: "2026-03-01T12:00:00Z", payload }));
      frame("connection.ready", {
        protocol_version: 1,
        connection_id: "e2e",
        last_event_id: 0,
        heartbeat_seconds: 20,
        idle_timeout_seconds: 60,
      });
      ws.onMessage((raw) => {
        const message = JSON.parse(String(raw)) as { type: string; topics?: string[] };
        if (message.type === "subscribe") (message.topics ?? []).forEach((t) => topics.add(t));
        if (message.type === "unsubscribe") (message.topics ?? []).forEach((t) => topics.delete(t));
        if (message.type === "subscribe" || message.type === "unsubscribe")
          frame("subscription.updated", { topics: [...topics].sort(), rejected: [] });
        if (message.type === "ping") frame("pong", { last_event_id: 0 });
      });
    },
  );
}

/** Answer every /api/ request. Call before navigating. */
export async function mockBackend(
  page: Page,
  options: { role?: Role; fixtures?: Fixtures; realtime?: "live" | "refused" } = {},
): Promise<void> {
  const role = options.role ?? "admin";
  const fixtures = options.fixtures ?? {};
  await mockRealtime(page, options.realtime ?? "live");
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const url = new URL(route.request().url());
      const method = route.request().method();
      const match = fixtures[`${method} ${url.pathname}`] ?? fixtures[url.pathname];
      const graphqlRequest =
        url.pathname === "/api/graphql"
          ? (route.request().postDataJSON() as { operationName?: string; variables?: LooseRecord })
          : null;
      const body =
        match === undefined
          ? graphqlRequest
            ? graphqlDefaults(
                String(graphqlRequest.operationName || ""),
                graphqlRequest.variables || {},
                fixtures,
                role,
              )
            : defaults(url, method, role)
          : typeof match === "function"
            ? match(url, method)
            : match;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    },
  );
}
