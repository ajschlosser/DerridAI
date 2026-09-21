/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, toRef } from "vue";
import { defineStore } from "pinia";
import { jobsState } from "../state/jobsState";

const ACTIVE = new Set(["queued", "running", "cancelling"]);

/** Background jobs, shared with the legacy runtime. Read-only for Vue code until the runtime stops owning them. */
export const useJobsStore = defineStore("jobs", () => {
  const jobs = toRef(jobsState, "jobs");
  const lastFetched = toRef(jobsState, "jobsLastFetched");
  const version = toRef(jobsState, "version");
  const activeJobs = computed(() => {
    void version.value;
    return jobs.value.filter((job) => ACTIVE.has(String(job.status)));
  });
  return { jobs, lastFetched, version, activeJobs };
});
