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

vi.mock("../../src/domain/sharedWorkspaceStorage", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  persistPrefs: vi.fn(),
}));
vi.mock("../../src/domain/sharedNavigation", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  syncUrl: vi.fn(),
}));

import "../../src/runtime/runtimeBridge";
import { state } from "../../src/domain/sharedUrlState";
import { jobsState } from "../../src/state/jobsState";
import { syncUrl } from "../../src/domain/sharedNavigation";
import { persistPrefs } from "../../src/domain/sharedWorkspaceStorage";
import { workDialogs } from "../../src/domain/sharedWorkDialogs";
import { worksWorkspace } from "../../src/domain/sharedWorksWorkspace";
import { refreshStoreWorks } from "../../src/domain/storeWorks";
import { worksService } from "../../src/services/works";

describe("shared Works workspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    jobsState.jobs = [];
    Object.assign(state, { files: [], activeFileId: null, userContext: null, worksSearch: "" });
  });

  it("reads the Works snapshot from the shared state alone", () => {
    expect(worksService.getSnapshot()).toBeTruthy();
  });

  it("binds Works background jobs to the shared jobs state", () => {
    jobsState.jobs = [{ id: "lookup", status: "running" }];
    expect(state.jobs).toBe(jobsState.jobs);
    state.jobs = [{ id: "replacement", status: "queued" }];
    expect(jobsState.jobs).toBe(state.jobs);
  });

  it("persists and syncs the URL when the Works query changes", () => {
    worksService.setQuery("glas");
    expect(state.worksSearch).toBe("glas");
    expect(persistPrefs).toHaveBeenCalled();
    expect(syncUrl).toHaveBeenCalledWith({ replace: true });
  });

  it("exposes the work dialogs the Works service opens", () => {
    for (const name of ["openSeparateWorksModal", "openWorkMetadataEditor", "openRemoveWorkModal"])
      expect(typeof (workDialogs as Record<string, unknown>)[name]).toBe("function");
    expect(typeof worksWorkspace.openWorkAnnotations).toBe("function");
  });

  it("clears the store's works without a request when no store is active", async () => {
    Object.assign(state, { activeStore: "", storeWorks: ["x"], storeWork: "x" });
    await refreshStoreWorks(true);
    expect(state.storeWorks).toEqual([]);
    expect(state.storeWork).toBe("");
  });
});
