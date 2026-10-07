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

import { afterEach, describe, expect, it, vi } from "vitest";
import { createPrefsPersistence, cancelPendingPrefs } from "../../src/domain/prefsPersistence";
import {
  setShellRefreshHook,
  shell,
  workspaceDbName,
} from "../../src/domain/sharedWorkspaceStorage";
import { sessionState } from "../../src/state/workspaceState";

afterEach(() => {
  vi.useRealTimers();
  cancelPendingPrefs();
  sessionState.userContext = null;
  sessionState.storageReady = false;
});

describe("prefs persistence over shared state", () => {
  it("debounces saves and writes nothing before storage is ready", async () => {
    vi.useFakeTimers();
    const put = vi.fn().mockResolvedValue(undefined);
    const state: Record<string, unknown> = {
      storageReady: false,
      reviewSelection: [],
      view: "home",
    };
    const { persistPrefs } = createPrefsPersistence({ state, put });
    persistPrefs();
    await vi.advanceTimersByTimeAsync(500);
    expect(put).not.toHaveBeenCalled();
    state.storageReady = true;
    persistPrefs();
    persistPrefs();
    await vi.advanceTimersByTimeAsync(500);
    expect(put).toHaveBeenCalledTimes(1);
    expect(put.mock.calls[0][0]).toBe("prefs");
    expect(put.mock.calls[0][1]).toMatchObject({ key: "workspace", view: "home" });
  });

  it("cancelPendingPrefs drops a queued save", async () => {
    vi.useFakeTimers();
    const put = vi.fn().mockResolvedValue(undefined);
    const { persistPrefs } = createPrefsPersistence({
      state: { storageReady: true, reviewSelection: [] },
      put,
    });
    persistPrefs();
    cancelPendingPrefs();
    await vi.advanceTimersByTimeAsync(500);
    expect(put).not.toHaveBeenCalled();
  });
});

describe("shared workspace storage", () => {
  it("names a researcher's database after the user and an admin's the default", () => {
    const admin = workspaceDbName();
    sessionState.userContext = { id: "u1", role: "researcher" };
    expect(workspaceDbName()).toBe(`${admin}-researcher-u1`);
    sessionState.userContext = { id: "a1", role: "admin" };
    expect(workspaceDbName()).toBe(admin);
  });

  it("shell refreshes the installed hook and ignores a non-function without owning persistence", () => {
    const hook = vi.fn();
    setShellRefreshHook(hook);
    shell();
    expect(hook).toHaveBeenCalledTimes(1);
    setShellRefreshHook(null);
    expect(() => shell()).not.toThrow();
  });
});
