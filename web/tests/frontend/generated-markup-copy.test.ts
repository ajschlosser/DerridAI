/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { createPdfExplorerCopy } from "../../src/domain/pdfExplorerCopy";
import { llmReviewDialogHtml } from "../../src/domain/jobReviewMarkup";

describe("PDF explorer copy module", () => {
  it("owns explorer strings so the Vue surface does not hardcode English", () => {
    const copy = createPdfExplorerCopy(
      (key, fallback = "") => (key === "pdf.explorer" ? "Explorateur PDF" : fallback),
      (_key, fallback, values = {}) =>
        Object.entries(values).reduce(
          (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
          fallback,
        ),
    );
    expect(copy.explorer).toBe("Explorateur PDF");
    expect(copy.pagesCount(3)).toBe("3 pages");
  });

  it("localizes extract fallbacks used by the live canvas renderer", () => {
    const copy = createPdfExplorerCopy(
      (key, fallback = "") =>
        key === "pdf.extract.file_gone"
          ? "Le fichier PDF n’est plus disponible dans cette session de navigateur."
          : fallback,
      (_key, fallback, values = {}) =>
        Object.entries(values).reduce(
          (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
          fallback,
        ),
    );
    expect(copy.fileGone).toBe(
      "Le fichier PDF n’est plus disponible dans cette session de navigateur.",
    );
    expect(copy.sourcePdfJsPage(4)).toBe("PDF.js (browser), page 4");
    expect(copy.pageMarker(2)).toBe("--- Page 2 ---");
  });
});

describe("LLM review markup module", () => {
  it("renders the dialog title from tr", () => {
    const html = llmReviewDialogHtml(
      {
        job: {
          mode: "review",
          completed: 2,
          total: 4,
          accepted_results: 0,
          accepted_fields: 0,
          rejected_results: 0,
          rejected_fields: 0,
          resolution_state: "pending",
        },
        flattened: [],
        unchanged: [],
        failures: [],
        selections: new Set(),
        successful: [],
        active: false,
        remaining: 0,
        pendingResults: 0,
        pendingChanges: 0,
        noChangeCount: 2,
        statusText: "done",
      },
      {
        tr: (key, fallback = "") =>
          key === "jobs.review.title" ? "Modifications de la revue LLM" : fallback,
        trf: (_key, fallback, values = {}) =>
          Object.entries(values).reduce(
            (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
            fallback,
          ),
        label: (key) => key,
        reviewDiffSides: () => ({ left: "", right: "" }),
        reviewKey: () => "k",
      },
    );
    expect(html).toContain("Modifications de la revue LLM");
    expect(html).not.toContain("LLM review changes");
  });
});

describe("LLM tool and record dialog markup", () => {
  const tr = (key: string, fallback = "") =>
    key === "records.merge.title" ? "Fusionner les onglets JSONL" : fallback;
  const trf = (_key: string, fallback: string, values: Record<string, unknown> = {}) =>
    Object.entries(values).reduce(
      (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
      fallback,
    );

  it("localizes merge dialog chrome", async () => {
    const { mergeDialogHtml } = await import("../../src/domain/recordDialogMarkup");
    const html = mergeDialogHtml([{ id: "1", name: "a.jsonl", records: [1, 2] }], { tr, trf });
    expect(html).toContain("Fusionner les onglets JSONL");
    expect(html).not.toContain("Merge JSONL tabs");
  });

  it("localizes LLM tool result actions", async () => {
    const { llmToolResultBody } = await import("../../src/domain/llmToolMarkup");
    const { actions } = llmToolResultBody(
      "pdf_clean_text",
      {},
      { text: "x" },
      {
        tr: (key, fallback = "") =>
          key === "jobs.tool.use_page_text" ? "Utiliser comme texte de page" : fallback,
        trf,
        ragGradeHtml: () => "",
      },
    );
    expect(actions).toContain("Utiliser comme texte de page");
    expect(actions).not.toContain("Use as current page text");
  });

  it("owns job dialog toasts through copy, not hardcoded English", async () => {
    const { createJobDialogCopy } = await import("../../src/domain/jobDialogCopy");
    const copy = createJobDialogCopy(
      (key, fallback = "") =>
        key === "jobs.toast.configure_provider"
          ? "Configurez d’abord un fournisseur LLM"
          : fallback,
      (_key, fallback) => fallback,
    );
    expect(copy.configureProvider).toBe("Configurez d’abord un fournisseur LLM");
  });
});
