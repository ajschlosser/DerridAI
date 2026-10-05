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
import type { ResearchThreadDetail, ResearchThreadSummary } from "../types/researchThreads";

const path = (id: string) => `/api/research/threads/${encodeURIComponent(id)}`;

/** Thread authority is SQLite; answer/evidence bodies use the existing authorized run APIs. */
export const researchThreadsApi = {
  list: (options: { offset?: number; search?: string; includeArchived?: boolean } = {}) => {
    const query = new URLSearchParams({
      limit: "50",
      offset: String(options.offset ?? 0),
      search: options.search ?? "",
      include_archived: String(options.includeArchived ?? false),
    });
    return apiRequest<{ threads: ResearchThreadSummary[] }>(`/api/research/threads?${query}`);
  },
  get: (id: string) => apiRequest<ResearchThreadDetail>(path(id)),
};
