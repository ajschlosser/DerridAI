/* Copyright 2026 Aaron John Schlosser, PhD. */
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import { jobsState, touchJobs } from "../../src/state/jobsState";
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
    (state.jobs[1] as { status: string }).status = "running";
    expect(store.activeJobs).toHaveLength(1);
    touchJobs();
    expect(store.version).toBe(1);
    expect(store.activeJobs).toHaveLength(2);
  });
});
