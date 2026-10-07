/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  nav: vi.fn(() => [{ id: "home", label: "Home", icon: "home", section: "Overview" }]),
  snapshot: vi.fn((options?: { projection?: string }) => {
    if (options?.projection === "context")
      return {
        view: "works",
        files: [{ id: "f1", name: "one.jsonl", count: 2, dirty: 0, active: true }],
        context: { kicker: "Corpora", title: "Works", meta: "" },
      };
    if (options?.projection === "status")
      return {
        totalLoaded: 2,
        corpusStoreCount: 1,
        dbRecords: 8,
        hasCorpusDb: true,
        activeStore: "primary",
        selectedEvidenceCount: 1,
      };
    return {};
  }),
}));

vi.mock("../../src/domain/navItems", () => ({ getNavItems: mocks.nav }));
vi.mock("../../src/domain/shellSnapshot", () => ({ getShellSnapshot: mocks.snapshot }));

import { useShellStore } from "../../src/stores/shell";

describe("shell store projection invalidation", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("keeps navigation stable during generic shell refreshes", () => {
    const shell = useShellStore();

    shell.syncNav();
    expect(mocks.nav).toHaveBeenCalledTimes(1);
    const nav = shell.snapshot.nav;

    shell.sync();
    shell.sync();

    expect(mocks.nav).toHaveBeenCalledTimes(1);
    expect(shell.snapshot.nav).toBe(nav);
    expect(shell.snapshot.context.title).toBe("Works");
    expect(shell.snapshot.totalLoaded).toBe(2);
  });

  it("can refresh context without recomputing status or navigation", () => {
    const shell = useShellStore();
    shell.syncNav();
    mocks.snapshot.mockClear();

    shell.syncContext();

    expect(mocks.snapshot).toHaveBeenCalledTimes(1);
    expect(mocks.snapshot).toHaveBeenCalledWith({
      projection: "context",
      includeNavigation: false,
    });
    expect(mocks.nav).toHaveBeenCalledTimes(1);
    expect(shell.snapshot.context.title).toBe("Works");
    expect(shell.snapshot.totalLoaded).toBe(0);
  });

  it("can refresh status without recomputing context or navigation", () => {
    const shell = useShellStore();
    shell.syncNav();
    mocks.snapshot.mockClear();

    shell.syncStatus();

    expect(mocks.snapshot).toHaveBeenCalledTimes(1);
    expect(mocks.snapshot).toHaveBeenCalledWith({
      projection: "status",
      includeNavigation: false,
    });
    expect(mocks.nav).toHaveBeenCalledTimes(1);
    expect(shell.snapshot.totalLoaded).toBe(2);
    expect(shell.snapshot.context.title).toBe("Dashboard");
  });
});
