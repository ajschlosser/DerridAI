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

const { put, remove, toast } = vi.hoisted(() => ({
  put: vi.fn(),
  remove: vi.fn(async () => undefined),
  toast: vi.fn(),
}));
vi.mock("../../src/domain/sharedWorkspaceStorage", () => ({
  workspaceDb: { get: vi.fn(), getAll: vi.fn(), put, remove },
  persistPrefs: vi.fn(),
  persistSettingsPreferences: vi.fn(),
  refreshShell: vi.fn(),
  shell: vi.fn(),
}));
vi.mock("../../src/domain/sharedNavigation", () => ({
  applyCompressedTableUrlState: vi.fn(),
  renderView: vi.fn(),
  syncUrl: vi.fn(),
}));
vi.mock("../../src/composables/notifications", () => ({ toast }));
vi.mock("../../src/composables/messageDialog", () => ({
  openMessageDialog: vi.fn(async () => true),
}));

import { clearFileDerivedState } from "../../src/domain/fileDerivedState";
import { stableJsonlFileIdentity } from "../../src/domain/jsonlIdentity";
import { closeFile, importFiles, triggerImport } from "../../src/domain/sharedFileLifecycle";
import { state } from "../../src/domain/sharedUrlState";
import { sessionState } from "../../src/state/workspaceState";

const jsonl = (text: string, name = "a.jsonl") => new File([text], name);

describe("file lifecycle", () => {
  beforeEach(() => {
    put.mockReset();
    remove.mockClear();
    toast.mockReset();
    state.files = [];
    state.activeFileId = null;
    sessionState.userContext = { id: "1", role: "admin" };
  });

  it("gives the same content the same identity", async () => {
    const a = await stableJsonlFileIdentity("x");
    expect(a).toEqual(await stableJsonlFileIdentity("x"));
    expect(a.id).not.toBe((await stableJsonlFileIdentity("y")).id);
    expect(a.id).toMatch(/^jsonl-[0-9a-f]{24}$/);
  });

  it("imports a file once, activates it and persists it", async () => {
    await importFiles([jsonl('{"record_id":"r1"}\n')]);
    await importFiles([jsonl('{"record_id":"r1"}\n')]);
    expect(state.files).toHaveLength(1);
    expect(state.files[0].records).toHaveLength(1);
    expect(state.activeFileId).toBe(state.files[0].id);
    expect(put).toHaveBeenCalledWith("files", expect.objectContaining({ id: state.files[0].id }));
    expect(toast).toHaveBeenLastCalledWith(expect.any(String), { tone: "warning" });
  });

  it("refuses imports for a researcher and for an account that cannot manage the corpus", async () => {
    sessionState.userContext = { id: "2", role: "researcher", capabilities: [] };
    await triggerImport([jsonl('{"record_id":"r1"}\n')]);
    await importFiles([jsonl('{"record_id":"r1"}\n')]);
    expect(state.files).toHaveLength(0);
    expect(toast).toHaveBeenCalledTimes(2);
    expect(toast).toHaveBeenCalledWith(expect.any(String), { tone: "warning" });
  });

  it("closes a file, drops its derived state and its saved copy", async () => {
    await importFiles([jsonl('{"record_id":"r1"}\n')]);
    const id = state.files[0].id;
    state.reviewSelection = new Set([`${id}::0`, "other::0"]);
    await closeFile(id);
    expect(state.files).toHaveLength(0);
    expect([...state.reviewSelection]).toEqual(["other::0"]);
    expect(remove).toHaveBeenCalledWith("files", id);
    expect(state.activeFileId).toBeNull();
  });

  it("clearFileDerivedState only touches keys of that file", () => {
    const s = {
      reviewSelection: new Set(["f::1", "g::1"]),
      selected: { f: 1, g: 2 },
      upsertState: { store: { "f::1": 1, "g::1": 2 } },
      upsertIgnored: {},
      storePresence: {},
      storePresenceIds: {},
      storePresenceCheckedAt: {},
    };
    clearFileDerivedState(s, "f");
    expect([...s.reviewSelection]).toEqual(["g::1"]);
    expect(s.selected).toEqual({ g: 2 });
    expect(s.upsertState.store).toEqual({ "g::1": 2 });
  });
});
