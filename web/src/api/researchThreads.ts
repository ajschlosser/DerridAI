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
import type {
  ResearchThread,
  ResearchThreadDetail,
  ResearchThreadSummary,
} from "../types/researchThreads";

const THREADS_PATH = "/api/research/threads";

/** Thread authority is SQLite; answer/evidence bodies use the existing authorized run APIs. */
export const researchThreadsApi = {
  importLegacy: (offset = 0) =>
    apiRequest<{ created: number; next_offset: number; has_more: boolean }>(
      `${THREADS_PATH}/import-legacy?offset=${offset}`,
      { method: "POST" },
    ),
  list: (options: { offset?: number; search?: string; includeArchived?: boolean } = {}) => {
    const query = new URLSearchParams({
      limit: "50",
      offset: String(options.offset ?? 0),
      search: options.search ?? "",
      include_archived: String(options.includeArchived ?? false),
    });
    return apiRequest<{ threads: ResearchThreadSummary[] }>(`${THREADS_PATH}?${query}`);
  },
  get: (id: string) =>
    apiRequest<ResearchThreadDetail>(`${THREADS_PATH}/${encodeURIComponent(id)}`),
  patch: (id: string, patch: { title?: string; archived?: boolean }) =>
    apiRequest<ResearchThread>(`${THREADS_PATH}/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  remove: (id: string) =>
    apiRequest<void>(`${THREADS_PATH}/${encodeURIComponent(id)}`, { method: "DELETE" }),
};
