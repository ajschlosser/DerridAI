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

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { jobsState, subscribeToJobChanges, touchJobs } from "../../src/state/jobsState";
import { createRuntimeState } from "../../src/runtime/runtimeState";
import { useJobsStore } from "../../src/stores/jobs";

describe("jobs state shared between the runtime and Vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    jobsState.jobs = [];
    jobsState.jobsLastFetched = 0;
    jobsState.jobApplied = {};
    jobsState.upsertJobApplied = {};
    jobsState.version = 0;
  });

  it("starts with the values the runtime always had", () => {
    const state = createRuntimeState();
    expect(state.jobs).toEqual([]);
    expect(state.jobsLastFetched).toBe(0);
    expect(state.jobApplied).toEqual({});
    expect(state.upsertJobApplied).toEqual({});
  });

  it("reads and writes the runtime fields through the shared state, unchanged for the runtime", () => {
    const state = createRuntimeState();
    const jobs = [{ id: "a", status: "running" }];
    state.jobs = jobs;
    // The runtime gets the very same array back, so it can keep mutating it in place.
    expect(state.jobs).toBe(jobs);
    state.jobs.push({ id: "b", status: "completed" });
    state.jobApplied["a"] = true;
    expect(jobsState.jobs).toBe(jobs);
    expect(jobsState.jobs).toHaveLength(2);
    expect(jobsState.jobApplied).toEqual({ a: true });
    expect(Object.keys(state)).toContain("jobs");
    expect(JSON.parse(JSON.stringify(state)).jobs).toHaveLength(2);
  });

  it("shows the jobs to Vue code and reports changes through the version", () => {
    const state = createRuntimeState();
    const store = useJobsStore();
    state.jobs = [
      { id: "a", status: "running" },
      { id: "b", status: "completed" },
    ];
    expect(store.jobs.map((job) => job.id)).toEqual(["a", "b"]);
    expect(store.activeJobs.map((job) => job.id)).toEqual(["a"]);
    // In-place edits are invisible to Vue until the runtime says something changed.
    (state.jobs[1] as unknown as { status: string }).status = "running";
    expect(store.activeJobs).toHaveLength(1);
    touchJobs();
    expect(store.version).toBe(1);
    expect(store.activeJobs).toHaveLength(2);
  });

  it("calls subscribers synchronously on every change, and stops when unsubscribed", () => {
    const calls: number[] = [];
    const stop = subscribeToJobChanges(() => calls.push(jobsState.version));
    touchJobs();
    expect(calls).toEqual([1]);
    touchJobs();
    expect(calls).toEqual([1, 2]);
    stop();
    touchJobs();
    expect(calls).toEqual([1, 2]);
  });

  it("keeps notifying other subscribers when one throws", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const seen: string[] = [];
    subscribeToJobChanges(() => {
      throw new Error("boom");
    });
    subscribeToJobChanges(() => seen.push("second"));
    touchJobs();
    expect(seen).toEqual(["second"]);
    expect(warn).toHaveBeenCalled();
  });
});
