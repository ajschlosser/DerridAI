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
