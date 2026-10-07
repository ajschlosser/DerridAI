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

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "../../src/composables/notifications";
import { createJobsWorkspace } from "../../src/domain/jobsWorkspace";
import { createRuntimeState } from "../../src/state/runtimeState";
import { jobsState } from "../../src/state/jobsState";
import { RealtimeClient } from "../../src/realtime/client";
import { MockSocket, jobEvent } from "./realtime-support";

vi.mock("../../src/composables/notifications", () => ({ toast: vi.fn() }));

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
      tr: (_key: string, fallback = "") => fallback,
      trf: (key: string, values: Record<string, unknown> = {}) =>
        `${key} ${Object.values(values).join(" ")}`,
      isActiveJobStatus: (status: string) => ["queued", "running", "cancelling"].includes(status),
      // Never started: behaves like the pre-realtime client.
      realtime: new RealtimeClient({ createSocket: (url) => new MockSocket(url) }),
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

  it("publishes job changes without rewriting application chrome DOM", async () => {
    document.body.innerHTML = '<button id="operationsBtn">Shell owns this</button>';
    const api = vi.fn(async () => ({ jobs: [{ id: "a", status: "running" }] }));
    const { spies, workspace } = setup({ api });

    await workspace.refreshJobs();

    expect(document.querySelector("#operationsBtn")?.textContent).toBe("Shell owns this");
    expect(spies.notifyOperationsChanged).toHaveBeenCalledTimes(1);
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

  describe("with the realtime socket", () => {
    function liveSetup(overrides: Record<string, unknown> = {}) {
      MockSocket.instances = [];
      const realtime = new RealtimeClient({
        createSocket: (url) => new MockSocket(url),
        url: () => "ws://t",
        random: () => 1,
      });
      const context = setup({ realtime, ...overrides });
      context.workspace.startRealtime();
      const socket = MockSocket.instances[0];
      socket.ready();
      return { ...context, realtime, socket };
    }

    it("replaces polling with events while the socket is healthy", () => {
      const api = vi.fn(async () => ({ jobs: [] }));
      const { state, workspace, socket } = liveSetup({ api });
      state.jobs = [{ id: "a", status: "running" }];
      workspace.startJobPolling();
      expect(state.jobsPollTimer ?? null).toBeNull();
      expect(socket.sent[0]).toEqual({ type: "subscribe", topics: ["jobs"] });
    });

    it("merges a job event through the shared reconciliation and notifies once", async () => {
      const api = vi.fn(async () => ({
        jobs: [{ id: "a", type: "llm", status: "completed", completed: 3, total: 3 }],
      }));
      const { state, spies, socket } = liveSetup({ api });
      await vi.advanceTimersByTimeAsync(0); // initial "connected" resync
      api.mockClear();
      state.jobs = [
        { id: "a", type: "llm", status: "running", completed: 1, total: 3, label: "LLM" },
      ];

      socket.frame(
        jobEvent(1, 1, { id: "a", type: "llm", status: "running", completed: 2, total: 3 }),
      );
      await vi.advanceTimersByTimeAsync(0);
      expect(state.jobs[0]).toMatchObject({ completed: 2, label: "LLM" });
      expect(spies.notifyOperationsChanged).toHaveBeenCalled();
      expect(api).not.toHaveBeenCalled();

      socket.frame(
        jobEvent(
          2,
          2,
          { id: "a", type: "llm", status: "completed", completed: 3 },
          "job.completed",
        ),
      );
      await vi.advanceTimersByTimeAsync(300);
      // The terminal summary is followed by one authoritative REST snapshot.
      expect(api).toHaveBeenCalledWith("/api/jobs");
      expect(state.jobs[0].status).toBe("completed");
      const completions = vi
        .mocked(toast)
        .mock.calls.filter(([message]) => String(message).includes("completed"));
      expect(completions).toHaveLength(1);
    });

    it("fetches the REST snapshot for jobs it has not loaded yet", async () => {
      const api = vi.fn(async () => ({ jobs: [{ id: "new", status: "queued" }] }));
      api.mockResolvedValueOnce({ jobs: [] });
      const { state, socket } = liveSetup({ api });
      await vi.advanceTimersByTimeAsync(300);
      api.mockClear();
      socket.frame(jobEvent(1, 1, { id: "new", status: "queued" }, "job.created"));
      await vi.advanceTimersByTimeAsync(300);
      expect(api).toHaveBeenCalledWith("/api/jobs");
      expect(state.jobs.map((job: { id: string }) => job.id)).toEqual(["new"]);
    });

    it("falls back to slow polling when the socket keeps failing, and closes on pause", async () => {
      const api = vi.fn(async () => ({ jobs: [{ id: "a", status: "running" }] }));
      const { state, workspace, realtime, socket } = liveSetup({ api });
      state.jobs = [{ id: "a", status: "running" }];
      socket.serverClose(1006);
      for (let i = 0; i < 3; i += 1) {
        await vi.runOnlyPendingTimersAsync();
        MockSocket.instances[MockSocket.instances.length - 1].serverClose(1006);
      }
      expect(realtime.fallbackActive).toBe(true);
      expect(state.jobsPollTimer).not.toBeNull();
      workspace.pauseRuntime();
      expect(state.jobsPollTimer).toBeNull();
      expect(realtime.status).toBe("idle");
    });
  });
});
