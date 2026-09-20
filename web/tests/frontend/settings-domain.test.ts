/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  filterSettingsFields,
  normalizeRag,
  resolveColorScheme,
  resolveContrast,
  sameSettings,
  validateRag,
  RAG_DEFAULTS,
} from "../../src/domain/settings";

describe("settings domain", () => {
  it("rejects empty document languages and retrieval routes", () => {
    const errors = validateRag({...RAG_DEFAULTS, locales: [], search_types: []});
    expect(errors.map(error => error.field).sort()).toEqual(["locales", "search_types"]);
  });

  it("requires fetch_k to cover retrieval k and total chars to cover per-record chars", () => {
    const errors = validateRag({...RAG_DEFAULTS, k: 80, fetch_k: 40, evidence_record_char_limit: 9000, evidence_total_char_limit: 8000});
    expect(errors.some(error => error.field === "fetch_k")).toBe(true);
    expect(errors.some(error => error.field === "evidence_total_char_limit")).toBe(true);
  });

  it("normalizes rag drafts without dropping user values after a failed save", () => {
    const draft = normalizeRag({k: 12, fetch_k: 12, locales: ["fr"], search_types: ["lexical"]});
    expect(draft.k).toBe(12);
    expect(draft.locales).toEqual(["fr"]);
    expect(draft.search_types).toEqual(["lexical"]);
    expect(sameSettings(draft, {...draft})).toBe(true);
  });

  it("keeps explicitly empty languages and routes so save validation can reject them", () => {
    const draft = normalizeRag({locales: [], search_types: []});
    expect(draft.locales).toEqual([]);
    expect(draft.search_types).toEqual([]);
  });

  it("filters searchable fields with translated labels", () => {
    const hits = filterSettingsFields("couleur", (key, fallback) => key === "settings.color_theme" ? "Thème de couleur" : fallback);
    expect(hits.some(field => field.id === "theme")).toBe(true);
  });

  it("resolves system color scheme and contrast without using color alone", () => {
    expect(resolveColorScheme("system", true)).toBe("dark");
    expect(resolveColorScheme("light", true)).toBe("light");
    expect(resolveContrast("system", true)).toBe("more");
    expect(resolveContrast("system", false)).toBe("default");
  });
});
