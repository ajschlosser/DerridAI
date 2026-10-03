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

import { apiRequest } from "./http";
export interface JobSummary {
  id: string;
  status: string;
  kind?: string;
  type?: string;
  mode?: string;
  tool?: string;
  label?: string;
  provider?: string;
  model?: string | null;
  provider_profile_id?: string | null;
  request?: Record<string, unknown> | null;
  stage?: string;
  stage_detail?: string;
  total?: number;
  completed?: number;
  failed?: number;
  result?: Record<string, unknown> | null;
  error?: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
  finished_at?: string | null;
}
export const jobsApi = {
  list: () => apiRequest<{ jobs: JobSummary[] }>("/api/jobs"),
  get: (id: string) => apiRequest<JobSummary>(`/api/jobs/${encodeURIComponent(id)}`),
};
