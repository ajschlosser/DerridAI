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
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 */

import { describe, expect, it, vi } from "vitest";

const h = vi.hoisted(() => ({
  legacyPersist: vi.fn(),
}));

vi.mock("../../src/domain/prefsPersistence", () => ({
  cancelPendingPrefs: vi.fn(),
  createPrefsPersistence: () => ({
    workspacePrefs: vi.fn(() => ({ key: "workspace" })),
    persistPrefs: h.legacyPersist,
    flushWorkspacePrefs: vi.fn(async () => undefined),
  }),
}));

import { setShellRefreshHook, shell } from "../../src/domain/sharedWorkspaceStorage";

describe("shell refresh boundary", () => {
  it("never schedules the legacy whole-workspace preference writer", () => {
    const refresh = vi.fn();
    setShellRefreshHook(refresh);

    shell();

    expect(refresh).toHaveBeenCalledTimes(1);
    expect(h.legacyPersist).not.toHaveBeenCalled();
  });
});
