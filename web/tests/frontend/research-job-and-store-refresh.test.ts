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

vi.mock("../../src/domain/legacyApi", () => ({
  api: vi.fn(async () => ({ stores: [{ name: "cache" }, { name: "corpus" }] })),
}));
vi.mock("../../src/domain/recordPayloads", () => ({
  isResponseCacheStore: (store: { name: string }) => store.name === "cache",
}));

import { createGetResearchJob } from "../../src/domain/researchJobLookup";
import { refreshStores } from "../../src/domain/sharedStores";
import { state } from "../../src/domain/sharedUrlState";
import { enhanceCollapsibles } from "../../src/domain/collapsiblePanels";

describe("createGetResearchJob", () => {
  it("merges a fetched job into the cached list and returns it for the UI", async () => {
    const state = {
      jobs: [{ id: "a", status: "running", keep: 1 }] as Array<
        Record<string, unknown> & { id: string }
      >,
    };
    const api = vi.fn(async () => ({ id: "a", type: "rag", status: "completed" }));
    const job = await createGetResearchJob({ api, state })("a/b");

    expect(api).toHaveBeenCalledWith("/api/jobs/a%2Fb");
    expect(state.jobs).toEqual([{ id: "a", status: "completed", keep: 1, type: "rag" }]);
    expect(job?.id).toBe("a");
  });

  it("adds a job the cache has not seen yet", async () => {
    const state = { jobs: [{ id: "old" }] as Array<Record<string, unknown> & { id: string }> };
    await createGetResearchJob({ api: async () => ({ id: "new", type: "rag" }), state })("new");
    expect(state.jobs.map((job) => job.id)).toEqual(["new", "old"]);
  });
});

describe("refreshStores", () => {
  it("loads the list and selects the first corpus store, never the response cache", async () => {
    state.activeStore = "gone";
    await refreshStores();
    expect(state.stores.map((store: { name: string }) => store.name)).toEqual(["cache", "corpus"]);
    expect(state.activeStore).toBe("corpus");
  });
});

describe("enhanceCollapsibles", () => {
  it("does nothing without a root", () => {
    expect(() => enhanceCollapsibles(null)).not.toThrow();
  });
});
