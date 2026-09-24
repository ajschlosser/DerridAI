import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import {
  operationDetailPairs,
  operationViewModel,
  setTranslationDictionary,
  state,
} from "../../src/runtime/runtime.js";
import { formatDuration } from "../../src/domain/operationsPanel";

// The Operations panel and its details dialog get their labels, fact names and sentence fragments from the
// runtime. Every one of them must come from a translation key. To prove it, load a pseudo-locale in which every
// known key translates to "⟦key⟧": any label that still reads as plain English was hard-coded.
const localeSource = readFileSync(resolve(process.cwd(), "../api/app/locales/en_us.py"), "utf8");
const KEYS = [...localeSource.matchAll(/^\s*'([^']+)':/gm)].map((m) => m[1]);
const pseudo = Object.fromEntries(KEYS.map((key) => [key, `⟦${key}⟧`]));

// Retrieval parameter names shown verbatim: identifiers, not prose, and the same in every language.
const LITERAL_PARAMETER_NAMES = new Set(["k / fetch_k", "RRF k"]);

const base = {
  status: "completed",
  total: 10,
  completed: 4,
  owner: "admin",
  created_at: "2026-09-20T10:00:00Z",
  started_at: "2026-09-20T10:00:05Z",
  finished_at: "2026-09-20T10:01:00Z",
};
const JOBS: Array<Record<string, any>> = [
  {
    id: "auto",
    type: "llm",
    mode: "auto",
    model: "m",
    provider: "p",
    fields: ["speaker"],
    current_record_id: "r-1",
    resolution_state: "partially_accepted",
    accepted_results: 1,
    accepted_fields: 2,
    rejected_results: 0,
    rejected_fields: 0,
    failed: 2,
  },
  { id: "review", type: "llm", mode: "manual", model: "m", pending_result_count: 2 },
  {
    id: "rag",
    type: "rag",
    stage: "retrieval",
    source_collection: "c",
    model: "m",
    request: { auto_grade: true, search_types: ["dense"], locales: ["fr-CA"] },
  },
  { id: "upsert", type: "upsert", store_name: "c", mirrored: { fr: 3 }, label: "" },
  {
    id: "pdf",
    type: "pdf_corpus",
    source_filename: "book.pdf",
    stage: "enriching",
    stage_detail: "backend text",
    record_count: 5,
    review_count: 1,
    unresolved_regions: 2,
  },
  ...["pdf_clean_text", "pdf_draft_record", "pdf_link_record", "rag_grade", "rag_grade_batch"].map(
    (tool) => ({
      id: tool,
      type: "llm_tool",
      tool,
      provider: "p",
      model: "m",
      request: { pdf_file: "x.pdf", response_record_id: "rr" },
    }),
  ),
  { id: "generic-tool", type: "llm_tool", provider: "p", model: "m" },
].map((job) => ({ ...base, ...job }));

describe("Operations legacy strings are translatable", () => {
  beforeEach(() => {
    setTranslationDictionary("fr-CA", pseudo, {});
  });

  const keyMarkersRemoved = (text: string) => text.replace(/⟦[^⟧]*⟧/g, "");

  it("every label, fact name and sentence fragment comes from a translation key", () => {
    for (const job of JOBS) {
      const view = operationViewModel(job);
      // A backend-supplied label (job.label) is data; everything the front end writes must be a key.
      if (!job.label) expect(view.label, `${job.id} label`).toContain("⟦");
      for (const [name] of operationDetailPairs(job)) {
        if (LITERAL_PARAMETER_NAMES.has(String(name))) continue;
        expect(String(name), `${job.id} fact "${name}"`).toContain("⟦");
      }
      // RAG, PDF corpus and LLM-tool subtitles are the backend's own stage text (data), not front-end strings.
      if (["llm", "upsert"].includes(job.type) && view.subtitle)
        expect(view.subtitle, `${job.id} subtitle`).toContain("⟦");
    }
  });

  it("no English word survives in the sentence fragments of an upsert or an LLM row", () => {
    const upsert = operationViewModel(JOBS.find((j) => j.id === "upsert")!);
    expect(keyMarkersRemoved(upsert.subtitle)).not.toMatch(/[a-z]{4,}/i);
    const auto = operationViewModel(JOBS.find((j) => j.id === "auto")!);
    expect(keyMarkersRemoved(auto.subtitle)).not.toMatch(/[a-z]{4,}/i);
  });

  it("the decision and result counts are translated, not raw enum text", () => {
    const pairs = operationDetailPairs(JOBS.find((j) => j.id === "auto")!);
    const byName = (name: string) =>
      pairs.find(([n]) => n === `⟦operations.fact.${name}⟧`)?.[1];
    expect(byName("decision")).toBe("⟦operations.decision.partially_accepted⟧");
    expect(byName("accepted")).toBe("⟦operations.fact.result_field_counts⟧");
    expect(byName("rejected")).toBe("⟦operations.fact.result_field_counts⟧");
  });

  it("progress text follows the language", () => {
    const view = operationViewModel({
      ...base,
      id: "p",
      type: "llm",
      status: "running",
      finished_at: null,
    });
    expect(view.progressLabel).toContain("⟦operations.progress_of⟧");
  });
});

describe("real French dictionary", () => {
  it("renders the same fields in French", () => {
    const fr = readFileSync(resolve(process.cwd(), "../api/app/locales/fr_ca.py"), "utf8");
    const dictionary: Record<string, string> = {};
    for (const m of fr.matchAll(/^\s*'(operations\.[^']+)':\s*'((?:[^'\\]|\\.)*)'/gm))
      dictionary[m[1]] = m[2].replaceAll("\\'", "'");
    setTranslationDictionary("fr-CA", dictionary, {});
    state.jobs = [];
    const auto = operationViewModel(JOBS.find((j) => j.id === "auto")!);
    expect(auto.label).toBe("Amélioration automatique");
    expect(auto.facts.map((f) => f.name)).toEqual(
      expect.arrayContaining(["Modèle", "Champs", "Fiche en cours"]),
    );
    expect(auto.subtitle).toMatch(/fiches/);
    expect(operationViewModel({ ...base, id: "rag", type: "rag", stage: "s" }).label).toBe(
      "Pipeline RAG",
    );
  });

  it("formats durations with Intl in the interface language", () => {
    expect(formatDuration(71, "fr-CA")).toMatch(/^1\s*min\s*11\s*s$/);
  });
});
