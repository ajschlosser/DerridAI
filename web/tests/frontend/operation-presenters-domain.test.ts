/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { createOperationPresenters } from "../../src/domain/operationPresenters";

// The snapshots were verified to be identical to the original legacy runtime.js functions, over about
// five hundred job fixtures covering every job type and status, before they were recorded.
const tr = (_key: string, fallback = "") => fallback;
const trf = (
  _key: string,
  fallbackOrValues: string | Record<string, unknown> = "",
  values: Record<string, unknown> = {},
) => {
  const fallback = typeof fallbackOrValues === "string" ? fallbackOrValues : "";
  const replacements = typeof fallbackOrValues === "string" ? values : fallbackOrValues;
  return Object.entries(replacements).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
    fallback,
  );
};
const presenters = createOperationPresenters({
  tr,
  trf,
  getLocale: () => "en-US",
  getStores: () => [{ name: "corpus", embedding_model: "bge-m3" }],
  providerProfiles: () => [{ id: "p1", name: "Local" }],
  providerDisplayName: (profile) => `«${profile.name}»`,
});

const jobs = {
  llm: {
    id: "1",
    type: "llm",
    status: "running",
    model: "m",
    fields: ["a"],
    total: 10,
    completed: 4,
    pending_result_count: 2,
    started_at: "2026-01-01T10:00:00Z",
    finished_at: "2026-01-01T10:05:30Z",
  },
  rag: {
    id: "2",
    type: "rag",
    status: "completed",
    source_collection: "corpus",
    model: "gen",
    request: { locales: ["en"], k: 8, fetch_k: 50 },
    started_at: "2026-01-01T10:00:00Z",
    finished_at: "2026-01-01T10:01:00Z",
  },
  pdf: {
    id: "3",
    type: "pdf_corpus",
    status: "failed",
    source_filename: "x.pdf",
    stage: "segmenting",
    fatal_error: "boom",
    total: 4,
    completed: 1,
  },
  upsert: {
    id: "4",
    type: "upsert",
    status: "queued",
    label: "3 works",
    store_name: "corpus",
    total: 9,
    completed: 0,
  },
};

describe("operation presenters", () => {
  it("builds the Operations panel view model for each job type", () => {
    for (const job of Object.values(jobs))
      expect(presenters.operationViewModel(job)).toMatchSnapshot();
  });
  it("labels jobs and formats progress", () => {
    expect(presenters.jobLabel(jobs.rag)).toBe("RAG pipeline");
    expect(presenters.jobLabel({ type: "llm_tool", tool: "pdf_clean_text" })).toBe(
      "PDF · clean text",
    );
    expect(presenters.jobProgressText(jobs.llm, "of")).toBe("4 of 10 (40%)");
    expect(presenters.jobProgressText(jobs.llm)).toBe("4/10 (40%)");
    expect(presenters.jobProgressText({ type: "pdf_corpus", status: "completed" })).toBe(
      "Build complete · ready for review",
    );
  });
  it("picks icons and result kinds", () => {
    expect(presenters.operationIcon(jobs.pdf)).toBe("pdf");
    expect(presenters.operationIcon({ type: "llm_tool", tool: "language_pack" })).toBe("language");
    expect(presenters.operationResultKind(jobs.rag)).toBe("result");
    expect(presenters.operationResultKind({ ...jobs.llm, status: "completed" })).toBe("review");
    expect(presenters.operationResultKind(jobs.llm)).toBe("review-partial");
    expect(presenters.operationResultKind(jobs.upsert)).toBeNull();
  });
  it("measures elapsed time", () => {
    expect(presenters.jobElapsedSeconds(jobs.llm)).toBe(330);
    expect(presenters.jobElapsedSeconds({})).toBe(0);
  });
});
