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

import { describe, expect, it, vi } from "vitest";
import { createUpdateSearchQuery } from "../../src/domain/searchQuery";
import { hasCapability, isResearcher } from "../../src/domain/sharedSession";
import { sessionState } from "../../src/state/workspaceState";

describe("createUpdateSearchQuery", () => {
  it("sets the query, resets the page, then persists and syncs the URL", () => {
    const state: Record<string, unknown> = { globalSearch: "old", globalPage: 4 };
    const persistPrefs = vi.fn();
    const syncUrl = vi.fn();
    const update = createUpdateSearchQuery({ state, persistPrefs, syncUrl });

    expect(update(" différance", { replace: false })).toBe(" différance");
    expect(state).toEqual({ globalSearch: " différance", globalPage: 1 });
    expect(persistPrefs).toHaveBeenCalledTimes(1);
    expect(syncUrl).toHaveBeenCalledWith({ replace: false });
    expect(update(null)).toBe("");
    expect(syncUrl).toHaveBeenLastCalledWith({ replace: true });
  });
});

describe("shared session checks", () => {
  it("treats a signed-out session as non-researcher and without capabilities", () => {
    sessionState.userContext = null;
    expect(isResearcher()).toBe(false);
    expect(hasCapability("annotations.read")).toBe(false);
  });

  it("treats any non-admin account as a researcher", () => {
    sessionState.userContext = { id: "u", role: "researcher", capabilities: [] } as never;
    expect(isResearcher()).toBe(true);
    sessionState.userContext = null;
  });
});
