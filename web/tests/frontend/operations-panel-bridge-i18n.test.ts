/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { createOperationsPanelBridge } from "../../src/domain/operationsPanelBridge";
import { englishDefault } from "../../src/i18n/englishDefault";

function presenters(locale: "en" | "fr") {
  const tr = (key: string, fallback = "") =>
    locale === "fr" && key === "rag.activity_title"
      ? "Activité du pipeline RAG"
      : locale === "fr" && key === "rag.empty"
        ? "Aucune opération RAG pour le moment. Lancez-en une ci-dessous."
        : fallback || englishDefault(key) || key;
  const trf = (key: string, fallback: string | Record<string, unknown> = "", values: Record<string, unknown> = {}) => {
    if (fallback && typeof fallback === "object") {
      values = fallback;
      fallback = "";
    }
    const template =
      locale === "fr" && key === "rag.activity_summary"
        ? "{active} en cours · {finished} résultat(s) passé(s) · l’étape, le modèle, les paramètres et le temps se mettent à jour automatiquement"
        : fallback || englishDefault(key) || key;
    return Object.entries(values).reduce(
      (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
      String(template),
    );
  };
  return createOperationsPanelBridge({
    state: { jobs: [], stores: [], appConfig: {}, health: {} },
    api: () => ({}),
    cancelBackgroundJob: () => ({}),
    formatTimestamp: () => "t",
    humanDuration: () => "1s",
    isResearcher: () => false,
    jobElapsedSeconds: () => 1,
    openJobDetails: () => ({}),
    openJobResults: () => ({}),
    openLlmTaskLauncher: () => ({}),
    openMessageModal: () => ({}),
    operationViewModel: () => ({}),
    persistPrefs: () => ({}),
    pruneClientJobState: () => ({}),
    ragGradeEvidencePayload: () => ({}),
    ragGradeHtml: () => "",
    refreshJobs: () => ({}),
    showAppModal: () => ({}),
    toast: () => ({}),
    tr,
    trf,
  } as never);
}

describe("RAG live panel i18n", () => {
  it("renders empty-state copy from tr, not hardcoded English, in French", () => {
    const html = presenters("fr").ragProgressPanelHtml();
    expect(html).toContain("Activité du pipeline RAG");
    expect(html).toContain("Aucune opération RAG pour le moment. Lancez-en une ci-dessous.");
    expect(html).not.toContain("RAG pipeline activity");
    expect(html).not.toContain("No RAG jobs yet");
  });

  it("keeps English fallbacks when the dictionary is English", () => {
    const html = presenters("en").ragProgressPanelHtml();
    expect(html).toContain("RAG pipeline activity");
    expect(html).toContain("No RAG jobs yet. Start one below.");
  });
});
