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
import { createResearchWorkspace } from "../../src/domain/researchWorkspace";
import { createRuntimeState } from "../../src/state/runtimeState";

type Anything = any;

// The rendered Research and Response Library views are covered by the legacy baseline's research and faq scenarios
// (recorded before this logic moved); these pin the commands and their permission checks.
function setup(overrides: Record<string, unknown> = {}) {
  const state = createRuntimeState() as unknown as Record<string, Anything>;
  state.ragConfig = { k: 64, skip_retrieval: true, source_collection: "" };
  const calls: string[] = [];
  const spies: Record<string, ReturnType<typeof vi.fn>> = {};
  const deps = new Proxy(
    { state, tr: (_key: string, fallback: string) => fallback, ...overrides } as Record<
      string,
      unknown
    >,
    {
      get: (target, name: string) => {
        if (name in target) return target[name];
        spies[name] ??= vi.fn(() => {
          if (name === "persistPrefs") calls.push(name);
        });
        return spies[name];
      },
    },
  );
  const workspace = createResearchWorkspace(deps as never) as Record<
    string,
    (...args: unknown[]) => Anything
  >;
  return { state, calls, spies, workspace };
}

describe("research workspace commands", () => {
  it("preserves thread linkage through the job presentation adapter", async () => {
    const { researchJobForUi } = await import("../../src/domain/researchPayloads");
    expect(
      researchJobForUi({ id: "j", thread_id: "t", turn_id: "u", status: "running" }),
    ).toMatchObject({ id: "j", thread_id: "t", turn_id: "u" });
  });
  it("accepts only known configuration keys and saves", () => {
    const { state, calls, spies, workspace } = setup({ selectedEvidenceEntries: () => [{}] });
    const config = workspace.updateResearchConfig({
      k: 8,
      prompt: "What is the trace?",
      unknown_key: 1,
    });
    expect(state.ragConfig).toMatchObject({
      k: 8,
      prompt: "What is the trace?",
      skip_retrieval: true,
    });
    expect(state.ragConfig).not.toHaveProperty("unknown_key");
    expect(config).toMatchObject({ k: 8 });
    expect(calls).toEqual(["persistPrefs"]);
    expect(spies.shellRefreshHook).toHaveBeenCalled();
  });

  it("turns off skipping retrieval when no evidence is selected", () => {
    const { state, workspace } = setup({ selectedEvidenceEntries: () => [] });
    workspace.updateResearchConfig({ k: 4 });
    expect(state.ragConfig.skip_retrieval).toBe(false);
  });

  it("refuses to change evidence without the permission", () => {
    const { workspace } = setup({ hasCapability: () => false });
    expect(() => workspace.removeResearchEvidence("k")).toThrow(
      "Your role cannot change selected evidence.",
    );
    expect(() => workspace.clearResearchEvidence()).toThrow(
      "Your role cannot change selected evidence.",
    );
  });

  it("removes one piece of evidence and returns what is left", () => {
    const { spies, workspace } = setup({
      hasCapability: () => true,
      selectedEvidenceEntries: () => [{ key: "k2", kind: "workspace", record_id: "r2" }],
    });
    const left = workspace.removeResearchEvidence("k1");
    expect(spies.setEvidence).toHaveBeenCalledWith("k1", null, false);
    expect(left.map((item: { record_id: string }) => item.record_id)).toEqual(["r2"]);
  });

  it("lists only Research jobs, and none for a researcher who may not manage jobs", async () => {
    const jobs = [
      { id: "a", type: "rag", status: "done" },
      { id: "b", type: "llm", status: "done" },
    ];
    const admin = setup({
      isResearcher: () => false,
      hasCapability: () => true,
      refreshJobs: async () => undefined,
    });
    admin.state.jobs = jobs;
    expect(
      (await admin.workspace.refreshResearchJobs()).map((job: { id: string }) => job.id),
    ).toEqual(["a"]);
    const researcher = setup({ isResearcher: () => true, hasCapability: () => false });
    expect(await researcher.workspace.refreshResearchJobs()).toEqual([]);
  });

  it("clamps the Response Library page request and checks access", async () => {
    const api = vi.fn(async () => ({ records: [] }));
    const { workspace } = setup({ canAccessPage: () => true, api });
    await workspace.getResponseFaqPage({ limit: 5000, offset: -3, query: "  trace " });
    expect(api).toHaveBeenCalledWith("/api/response-cache/records?limit=1000&offset=0&query=trace");
    const denied = setup({ canAccessPage: () => false });
    await expect(denied.workspace.getResponseFaqPage()).rejects.toThrow(
      "Your role cannot open Response Library.",
    );
  });
});

describe("Research independent reads", () => {
  it("can hydrate composer data without waiting for run history or pipeline visibility", async () => {
    const refreshJobs = vi.fn(() => new Promise(() => {})),
      api = vi.fn(() => new Promise(() => {}));
    const { workspace } = setup({
      refreshStores: vi.fn(async () => {}),
      refreshJobs,
      api,
      recordStores: () => [],
      providerProfiles: () => [],
      selectedEvidenceEntries: () => [],
      hasCorpusDb: () => false,
      hasCapability: () => true,
      isResearcher: () => false,
    });
    const result = await workspace.getResearchWorkspaceSnapshot({
      refresh: true,
      includeJobs: false,
      includePipelines: false,
      strictCollections: true,
    });
    expect(result.stores).toEqual([]);
    expect(refreshJobs).not.toHaveBeenCalled();
    expect(api).not.toHaveBeenCalled();
  });
  it("reports a failed authoritative collection read instead of confirming an empty workspace", async () => {
    const { workspace } = setup({
      refreshStores: vi.fn(async () => {
        throw new Error("Collections unavailable");
      }),
    });
    await expect(
      workspace.getResearchWorkspaceSnapshot({ refresh: true, strictCollections: true }),
    ).rejects.toThrow("Collections unavailable");
  });
});
