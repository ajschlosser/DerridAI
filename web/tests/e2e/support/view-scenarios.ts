/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Locator, Page } from "@playwright/test";
import { FAQ_RECORDS, LANGUAGES, type Fixtures, type Role } from "./mock-backend";

// Distinct states of the Vue views that no Storybook story renders (Languages, Response Library and
// Record). Each is reached in the real app against the mock backend, so the shell, the router and
// the runtime are all in play.
export interface Scenario {
  id: string;
  path: string;
  role?: Role;
  fixtures?: Fixtures;
  /** Something that is visible once the state has been reached. */
  ready: (page: Page) => Locator;
  /** Interactions that reach the state, after the page has loaded. */
  steps?: (page: Page) => Promise<void>;
}

const faqPage = {
  records: FAQ_RECORDS,
  count: FAQ_RECORDS.length,
  total: FAQ_RECORDS.length,
  limit: 50,
  offset: 0,
  exists: true,
};

const translationReport = {
  status: "completed_with_fallbacks",
  source_locale: "en-US",
  provider: "ollama",
  model: "gemma4:12b",
  completed_at: "2026-09-01T00:00:00Z",
  key_count: 902,
  translated_count: 897,
  failed_count: 3,
  fallback_count: 2,
  failed_keys: [
    "pdf_corpus.metadata_enrichment_again_help",
    "faq.grade_risky_claims",
    "runtime.no_records",
  ],
  failures: [
    {
      key: "faq.grade_risky_claims",
      reason: "Placeholder {count} was dropped from the translation.",
    },
  ],
};
const runningJob = {
  id: "job-lang-1",
  status: "running",
  mode: "language_dictionary",
  label: "Languages · de-DE",
  stage: "translating",
  stage_detail: "Batch 3 of 9",
  total: 902,
  completed: 310,
  failed: 0,
  request: { code: "de-DE", name: "Deutsch" },
};

export const scenarios: Scenario[] = [
  // Languages
  {
    id: "languages-default",
    path: "/languages",
    ready: (p) => p.getByRole("heading", { name: /Languages & internationalization/ }),
  },
  {
    id: "languages-policy-needed",
    path: "/languages",
    ready: (p) => p.getByRole("heading", { name: /Deutsch/ }),
    steps: async (p) => {
      await p.getByRole("button", { name: /de-DE/ }).click();
    },
  },
  {
    id: "languages-install-dialog",
    path: "/languages",
    ready: (p) => p.getByRole("dialog"),
    steps: async (p) => {
      await p.getByRole("button", { name: /Install language/ }).click();
    },
  },
  {
    id: "languages-translation-report",
    path: "/languages",
    fixtures: {
      "/api/i18n/languages/fr-CA": {
        ...LANGUAGES[1],
        dictionary: { "common.close": "Fermer" },
        translation_report: translationReport,
      },
    },
    ready: (p) => p.getByRole("heading", { name: /Français/ }),
    steps: async (p) => {
      await p.getByRole("button", { name: /fr-CA/ }).click();
    },
  },
  {
    id: "languages-job-running",
    path: "/languages",
    fixtures: { "/api/jobs": { jobs: [runningJob] }, "/api/jobs/job-lang-1": runningJob },
    ready: (p) => p.getByText(/Batch 3 of 9/).first(),
  },
  // Response Library
  { id: "faq-empty", path: "/faq", ready: (p) => p.getByRole("main") },
  {
    id: "faq-records",
    path: "/faq",
    fixtures: { "/api/response-cache/records": faqPage },
    ready: (p) => p.getByText(/How does Derrida distinguish/).first(),
  },
  {
    id: "faq-archive-dialog",
    path: "/faq",
    fixtures: { "/api/response-cache/records": faqPage },
    ready: (p) => p.getByRole("dialog"),
    steps: async (p) => {
      await p
        .getByRole("button", { name: /Browse saved research/ })
        .first()
        .click();
    },
  },
  // Settings and Compare
  { id: "settings-default", path: "/settings", ready: (p) => p.getByRole("heading", { level: 1 }) },
  { id: "compare-default", path: "/compare", ready: (p) => p.getByRole("heading", { level: 1 }) },
  // Record (a researcher reads a record from the database)
  {
    id: "record-overview",
    path: "/record",
    role: "researcher",
    ready: (p) => p.getByRole("heading", { name: /On Cosmopolitanism/ }),
  },
  {
    id: "record-provenance",
    path: "/record",
    role: "researcher",
    ready: (p) => p.getByRole("tab", { name: "Provenance", selected: true }),
    steps: async (p) => {
      await p.getByRole("tab", { name: "Provenance" }).click();
    },
  },
  {
    id: "record-annotations",
    path: "/record",
    role: "researcher",
    ready: (p) => p.getByRole("tab", { name: "Annotations", selected: true }),
    steps: async (p) => {
      await p.getByRole("tab", { name: "Annotations" }).click();
    },
  },
  {
    id: "record-empty",
    path: "/record",
    role: "researcher",
    fixtures: { "/api/stores": { stores: [] } },
    ready: (p) => p.getByRole("main"),
  },
];
