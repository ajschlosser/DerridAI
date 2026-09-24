/* Copyright 2026 Aaron John Schlosser, PhD. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createJobsWorkspace } from "../../src/domain/jobsWorkspace";
import { createRuntimeState } from "../../src/runtime/runtimeState";
import { jobsState } from "../../src/state/jobsState";

type Anything = any;

// The dashboard's job scenarios (polling, refresh, cancel, remove, clear) are covered by the legacy baseline, recorded
// before this logic moved; these pin the state handling that does not need a rendered page.
function setup(overrides: Record<string, unknown> = {}) {
  const state = createRuntimeState() as unknown as Record<string, Anything>;
  state.view = "home";
  state.ragConfig = { run_history: [{ job_id: "a" }, { job_id: "b" }] };
  const spies: Record<string, ReturnType<typeof vi.fn>> = {};
  const deps = new Proxy(
    {
      state,
      isActiveJobStatus: (status: string) => ["queued", "running", "cancelling"].includes(status),
      ...overrides,
    } as Record<string, unknown>,
    {
      get: (target, name: string) => {
        if (name in target) return target[name];
        spies[name] ??= vi.fn();
        return spies[name];
      },
    },
  );
  const workspace = createJobsWorkspace(deps as never) as Record<
    string,
    (...args: unknown[]) => Anything
  >;
  return { state, spies, workspace };
}

describe("jobs workspace", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    jobsState.jobs = [];
  });
  afterEach(() => {
    vi.useRealTimers();
    jobsState.jobs = [];
  });

  it("never starts an idle polling loop", () => {
    const { state, workspace } = setup();
    state.jobs = [{ id: "a", status: "completed" }];
    workspace.startJobPolling();
    expect(state.jobsPollTimer ?? null).toBeNull();
  });

  it("schedules a poll while a job is active, and stops when paused", async () => {
    const jobs = [{ id: "a", status: "running" }];
    const { state, spies, workspace } = setup({
      api: vi.fn(async () => ({ jobs: jobs.map((job) => ({ ...job })) })),
    });
    state.jobs = jobs;
    workspace.startJobPolling();
    expect(state.jobsPollTimer).not.toBeNull();
    workspace.pauseRuntime();
    expect(state.jobsPollTimer).toBeNull();
    expect(spies.api).toBeUndefined();
  });

  it("registers a job started elsewhere at the front of the list and starts polling", () => {
    const { state, spies, workspace } = setup();
    state.jobs = [{ id: "old", status: "completed" }];
    workspace.registerExternalJob({ id: "new", status: "running" });
    expect(state.jobs.map((job: { id: string }) => job.id)).toEqual(["new", "old"]);
    expect(state.jobsPollTimer).not.toBeNull();
    expect(spies.shell).toHaveBeenCalled();
    workspace.registerExternalJob({ status: "running" });
    expect(state.jobs).toHaveLength(2);
    workspace.pauseRuntime();
  });

  it("forgets everything about a removed job", () => {
    const { state, spies, workspace } = setup();
    state.jobs = [{ id: "a" }, { id: "b" }];
    state.jobApplied = { a: true, b: true };
    state.upsertJobApplied = { a: true };
    workspace.pruneClientJobState("a");
    expect(state.jobs.map((job: { id: string }) => job.id)).toEqual(["b"]);
    expect(state.jobApplied).toEqual({ b: true });
    expect(state.upsertJobApplied).toEqual({});
    expect(state.ragConfig.run_history).toEqual([{ job_id: "b" }]);
    expect(spies.updateOperationStackCount).toHaveBeenCalled();
    workspace.pruneClientJobState("b", { removeHistory: false });
    expect(state.ragConfig.run_history).toEqual([{ job_id: "b" }]);
  });

  it("removes a finished job on the server, then in the client, then refreshes", async () => {
    const api = vi.fn(async (path: string) => (path === "/api/jobs" ? { jobs: [] } : { ok: true }));
    const { state, spies, workspace } = setup({ api });
    state.jobs = [{ id: "a" }];
    await workspace.removeFinishedJob("a");
    expect(api).toHaveBeenNthCalledWith(1, "/api/jobs/a", { method: "DELETE" });
    expect(state.jobs).toEqual([]);
    expect(spies.persistPrefs).toHaveBeenCalled();
    expect(api).toHaveBeenCalledWith("/api/jobs");
  });
});
