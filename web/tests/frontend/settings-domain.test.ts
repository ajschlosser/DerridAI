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

import { describe, expect, it } from "vitest";
import {
  filterSettingsFields,
  normalizeRag,
  resolveColorScheme,
  resolveContrast,
  resolveSettingsSectionId,
  SETTINGS_SECTIONS,
  sameSettings,
  validateRag,
  RAG_DEFAULTS,
} from "../../src/domain/settings";

describe("settings domain", () => {
  it("rejects empty document languages and retrieval routes", () => {
    const errors = validateRag({ ...RAG_DEFAULTS, locales: [], search_types: [] });
    expect(errors.map((error) => error.field).sort()).toEqual(["locales", "search_types"]);
  });

  it("requires fetch_k to cover retrieval k and total chars to cover per-record chars", () => {
    const errors = validateRag({
      ...RAG_DEFAULTS,
      k: 80,
      fetch_k: 40,
      evidence_record_char_limit: 9000,
      evidence_total_char_limit: 8000,
    });
    expect(errors.some((error) => error.field === "fetch_k")).toBe(true);
    expect(errors.some((error) => error.field === "evidence_total_char_limit")).toBe(true);
  });

  it("normalizes rag drafts without dropping user values after a failed save", () => {
    const draft = normalizeRag({
      k: 12,
      fetch_k: 12,
      automatic_sizing: true,
      locales: ["fr"],
      search_types: ["lexical"],
    });
    expect(draft.k).toBe(12);
    expect(draft.automatic_sizing).toBe(true);
    expect(draft.locales).toEqual(["fr"]);
    expect(draft.search_types).toEqual(["lexical"]);
    expect(sameSettings(draft, { ...draft })).toBe(true);
  });

  it("keeps explicitly empty languages and routes so save validation can reject them", () => {
    const draft = normalizeRag({ locales: [], search_types: [] });
    expect(draft.locales).toEqual([]);
    expect(draft.search_types).toEqual([]);
  });

  it("maps legacy settings routes onto task-oriented categories", () => {
    expect(resolveSettingsSectionId("workspace")).toBe("preferences");
    expect(resolveSettingsSectionId("review")).toBe("research");
    expect(resolveSettingsSectionId("providers")).toBe("services");
    expect(resolveSettingsSectionId("system")).toBe("data");
    expect(resolveSettingsSectionId("overview")).toBe("overview");
    expect(resolveSettingsSectionId("unknown")).toBeNull();
    expect(SETTINGS_SECTIONS[0]?.id).toBe("overview");
  });

  it("filters searchable fields with translated labels", () => {
    const hits = filterSettingsFields("couleur", (key, fallback) =>
      key === "settings.color_theme" ? "Thème de couleur" : fallback,
    );
    expect(hits.some((field) => field.id === "theme")).toBe(true);
  });

  it("resolves system color scheme and contrast without using color alone", () => {
    expect(resolveColorScheme("system", true)).toBe("dark");
    expect(resolveColorScheme("light", true)).toBe("light");
    expect(resolveContrast("system", true)).toBe("more");
    expect(resolveContrast("system", false)).toBe("default");
  });
});
