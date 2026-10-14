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

import { beforeEach, describe, expect, it, vi } from "vitest";

const h = vi.hoisted(() => ({
  sessionState: { storageReady: true },
  cancelPrefs: vi.fn(),
  cancelDomains: vi.fn(),
  cancelFiles: vi.fn(),
  flushFiles: vi.fn(async () => undefined),
  flushWorkspace: vi.fn(async () => undefined),
  flushDomain: vi.fn(async (_name: string) => undefined),
  close: vi.fn(),
}));

vi.mock("../../src/state/workspaceState", () => ({ sessionState: h.sessionState }));
vi.mock("../../src/domain/prefsPersistence", () => ({ cancelPendingPrefs: h.cancelPrefs }));
vi.mock("../../src/domain/sharedWorkspacePersistence", () => ({
  cancelPendingFileWrites: h.cancelFiles,
  flushPendingFileWrites: h.flushFiles,
}));
vi.mock("../../src/domain/sharedWorkspaceStorage", () => ({
  cancelPendingDomainPreferences: h.cancelDomains,
  flushDomainPreferences: h.flushDomain,
  flushWorkspacePrefs: h.flushWorkspace,
  workspaceDb: { close: h.close },
}));

import {
  flushWorkspaceSessionWrites,
  resetWorkspaceSessionPersistence,
} from "../../src/domain/workspaceSessionPersistence";
import { DOMAIN_PREFERENCE_KEYS } from "../../src/domain/domainPreferencePersistence";

describe("workspace session persistence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    h.sessionState.storageReady = true;
  });

  it("flushes every pending persistence layer before an authenticated session changes", async () => {
    await flushWorkspaceSessionWrites();

    expect(h.flushFiles).toHaveBeenCalledTimes(1);
    expect(h.flushWorkspace).toHaveBeenCalledTimes(1);
    expect(h.flushDomain.mock.calls.map(([name]) => name).sort()).toEqual(
      Object.keys(DOMAIN_PREFERENCE_KEYS).sort(),
    );
  });

  it("cancels delayed writes and closes the cached database before rebinding identity", () => {
    resetWorkspaceSessionPersistence();

    expect(h.sessionState.storageReady).toBe(false);
    expect(h.cancelPrefs).toHaveBeenCalledTimes(1);
    expect(h.cancelDomains).toHaveBeenCalledTimes(1);
    expect(h.cancelFiles).toHaveBeenCalledTimes(1);
    expect(h.close).toHaveBeenCalledTimes(1);
  });
});
