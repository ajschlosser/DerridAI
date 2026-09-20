/* Copyright 2026 Aaron John Schlosser, PhD. */
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
  if (path === "/api/response-cache/records")
    return { records: [], count: 0, total: 0, limit: 50, offset: 0, exists: true };
  return {};
}

/** Answer every /api/ request. Call before navigating. */
export async function mockBackend(
  page: Page,
  options: { role?: Role; fixtures?: Fixtures } = {},
): Promise<void> {
  const role = options.role ?? "admin";
  const fixtures = options.fixtures ?? {};
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const url = new URL(route.request().url());
      const method = route.request().method();
      const match = fixtures[`${method} ${url.pathname}`] ?? fixtures[url.pathname];
      const body =
        match === undefined
          ? defaults(url, method, role)
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
