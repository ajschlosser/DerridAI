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

import { nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";

const runtime = vi.hoisted(() => ({
  getRecordsListSnapshot: vi.fn(() => ({ files: [], columns: [] })),
  ensureCorpusWorkspaceLoaded: vi.fn(async () => undefined),
  state: { view: "" },
}));
vi.mock("../../src/domain/appBootstrap", () => ({ ...runtime }));
vi.mock("../../src/domain/sharedCorpusHydration", () => ({
  ensureCorpusWorkspaceLoaded: () => runtime.ensureCorpusWorkspaceLoaded(),
}));
vi.mock("../../src/domain/sharedRecordsWorkspace", () => ({ recordsWorkspace: runtime }));

import { useRecordsWorkspace } from "../../src/composables/useRecordsWorkspace";
import { corpusState, touchCorpus } from "../../src/state/workspaceState";

describe("useRecordsWorkspace refreshes when the loaded corpus changes", () => {
  it("reads the snapshot again after the corpus changes, once it has been loaded", async () => {
    const records = useRecordsWorkspace();
    touchCorpus();
    await nextTick();
    // Nothing was loaded yet, so a change does not load anything on its own.
    expect(runtime.getRecordsListSnapshot).not.toHaveBeenCalled();

    records.load();
    expect(runtime.getRecordsListSnapshot).toHaveBeenCalledTimes(1);
    touchCorpus();
    await nextTick();
    expect(runtime.getRecordsListSnapshot).toHaveBeenCalledTimes(2);

    corpusState.activeFileId = "f2";
    await nextTick();
    expect(runtime.getRecordsListSnapshot).toHaveBeenCalledTimes(3);
    corpusState.activeFileId = null;
  });

  it("tries to auto-load the corpus from Chroma when activated with nothing loaded", async () => {
    const records = useRecordsWorkspace();
    await records.activate();
    expect(runtime.ensureCorpusWorkspaceLoaded).toHaveBeenCalled();
  });
});
