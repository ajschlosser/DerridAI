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

import { researchJobForUi } from "./researchPayloads";

type Loose = Record<string, unknown>;
type Deps = {
  api: (path: string) => Promise<Loose & { id: string }>;
  state: Record<string, unknown>;
};

// Fetch one job from the server, merge it into the cached job list and return it shaped for the Research view.
export function createGetResearchJob({ api, state }: Deps) {
  return async function getResearchJob(jobId: unknown) {
    const job = await api(`/api/jobs/${encodeURIComponent(String(jobId))}`);
    const jobs = state.jobs as Array<Loose & { id: string }>;
    const index = jobs.findIndex((item) => item.id === job.id);
    if (index >= 0) jobs[index] = { ...jobs[index], ...job };
    else jobs.unshift(job);
    return researchJobForUi(job);
  };
}
