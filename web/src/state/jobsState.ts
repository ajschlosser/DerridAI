/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReactive } from "vue";

// Background-job state that used to live only on the legacy runtime's `state` object. It is one shared,
// shallow-reactive object: the runtime reads and writes it through accessors on its own `state` (so its code is
// unchanged), and Vue code reads it through `useJobsStore`.
//
// It is shallow on purpose. The runtime mutates the job list and the job records in place, and it must keep
// receiving the same plain objects it always did. Vue code learns about changes through `version`, which the
// runtime bumps at the points where it already tells the Operations panel that something changed.

export type JobRecord = Record<string, unknown> & { id: string };

export interface JobsState {
  jobs: JobRecord[];
  jobsLastFetched: number;
  /** Job ids whose finished results were already applied to the workspace. */
  jobApplied: Record<string, unknown>;
  upsertJobApplied: Record<string, unknown>;
  /** Bumped whenever the runtime reports a change to the jobs, so Vue code can watch it. */
  version: number;
}

export const jobsState = shallowReactive<JobsState>({
  jobs: [],
  jobsLastFetched: 0,
  jobApplied: {},
  upsertJobApplied: {},
  version: 0,
});

export const JOBS_RUNTIME_KEYS = [
  "jobs",
  "jobsLastFetched",
  "jobApplied",
  "upsertJobApplied",
] as const;

export function touchJobs(): void {
  jobsState.version += 1;
}

/** Makes `target[key]` read and write the shared jobs state, keeping the property enumerable like the plain field it replaces. */
export function bindJobsState<T extends object>(
  target: T,
): T & Pick<JobsState, (typeof JOBS_RUNTIME_KEYS)[number]> {
  for (const key of JOBS_RUNTIME_KEYS) {
    Object.defineProperty(target, key, {
      enumerable: true,
      configurable: true,
      get: () => jobsState[key],
      set: (value) => {
        (jobsState as unknown as Record<string, unknown>)[key] = value;
      },
    });
  }
  return target as T & Pick<JobsState, (typeof JOBS_RUNTIME_KEYS)[number]>;
}
