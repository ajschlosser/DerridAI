/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  applyDomainPreferenceRecord,
  createDomainPreferencePersistence,
  domainPreferenceRecord,
} from "../../src/domain/domainPreferencePersistence";

afterEach(() => {
  vi.useRealTimers();
});

describe("domain preference persistence", () => {
  it("serializes only the owning domain", () => {
    const state = {
      globalSearch: "trace",
      globalPage: 3,
      searchFacetFilters: { work: ["Glas"] },
      ragConfig: { prompt: "must not leak" },
      files: [{ id: "large-corpus" }],
      sidebarCollapsed: true,
    };

    const search = domainPreferenceRecord(state, "search");
    const layout = domainPreferenceRecord(state, "layout");

    expect(search).toMatchObject({
      key: "search-preferences",
      globalSearch: "trace",
      globalPage: 3,
      searchFacetFilters: { work: ["Glas"] },
    });
    expect(search).not.toHaveProperty("ragConfig");
    expect(search).not.toHaveProperty("files");
    expect(search).not.toHaveProperty("sidebarCollapsed");

    expect(layout).toMatchObject({
      key: "layout-preferences",
      sidebarCollapsed: true,
    });
    expect(layout).not.toHaveProperty("globalSearch");
    expect(layout).not.toHaveProperty("files");
  });

  it("uses independent debounce timers so one domain cannot cancel another", async () => {
    vi.useFakeTimers();
    const put = vi.fn().mockResolvedValue(undefined);
    const state = {
      storageReady: true,
      globalSearch: "first",
      sidebarCollapsed: false,
      reviewSelection: new Set<string>(),
      selectedEvidence: {},
    };
    const persistence = createDomainPreferencePersistence({ state, put, delay: 100 });

    persistence.persistSearchPreferences();
    state.sidebarCollapsed = true;
    persistence.persistLayoutPreferences();
    state.globalSearch = "second";
    persistence.persistSearchPreferences();

    await vi.advanceTimersByTimeAsync(110);

    expect(put).toHaveBeenCalledTimes(2);
    expect(put.mock.calls.map((call) => (call[1] as { key: string }).key).sort()).toEqual([
      "layout-preferences",
      "search-preferences",
    ]);
    expect(
      put.mock.calls.find((call) => (call[1] as { key: string }).key === "search-preferences")?.[1],
    ).toMatchObject({ globalSearch: "second" });
  });

  it("restores domain records over legacy values and rebuilds review selection as a Set", () => {
    const state: Record<string, unknown> = {
      globalSearch: "legacy",
      globalPage: 9,
      sidebarCollapsed: false,
      reviewSelection: new Set(["old"]),
      selectedEvidence: {},
    };

    applyDomainPreferenceRecord(state, {
      key: "search-preferences",
      globalSearch: "domain",
      globalPage: 2,
    });
    applyDomainPreferenceRecord(state, {
      key: "layout-preferences",
      sidebarCollapsed: true,
    });
    applyDomainPreferenceRecord(state, {
      key: "review-preferences",
      reviewSelection: ["a", "b"],
      selectedEvidence: { a: { key: "a" } },
    });

    expect(state.globalSearch).toBe("domain");
    expect(state.globalPage).toBe(2);
    expect(state.sidebarCollapsed).toBe(true);
    expect(state.reviewSelection).toBeInstanceOf(Set);
    expect([...(state.reviewSelection as Set<string>)]).toEqual(["a", "b"]);
    expect(state.selectedEvidence).toEqual({ a: { key: "a" } });
  });

  it("does not write before workspace storage is ready and can cancel all domains", async () => {
    vi.useFakeTimers();
    const put = vi.fn().mockResolvedValue(undefined);
    const state = {
      storageReady: false,
      globalSearch: "trace",
      sidebarCollapsed: true,
      reviewSelection: new Set<string>(),
      selectedEvidence: {},
    };
    const persistence = createDomainPreferencePersistence({ state, put, delay: 100 });

    persistence.persistSearchPreferences();
    await vi.advanceTimersByTimeAsync(110);
    expect(put).not.toHaveBeenCalled();

    state.storageReady = true;
    persistence.persistSearchPreferences();
    persistence.persistLayoutPreferences();
    persistence.cancelPendingDomainPreferences();
    await vi.advanceTimersByTimeAsync(110);
    expect(put).not.toHaveBeenCalled();
  });
});
