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
  ChromaConnectionUpdate,
  ChromaHealth,
  VectorCollection,
  VectorRecord,
  VectorSearchResult,
  VectorWorkStat,
} from "../types/vector";

/** The versioned store-search pipeline that produced a result set. */
export type StoreSearchPipelineIdentity = {
  feature: string;
  pipeline_id: string;
  pipeline_version: number;
  pipeline_hash: string;
  trace_id: string;
  trace_warning?: string;
};

export const chromaApi = {
  health: () => apiRequest<ChromaHealth>("/api/chroma/connection"),
  probe: (body: ChromaConnectionUpdate) =>
    apiRequest<ChromaHealth>("/api/chroma/connection/probe", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  setConnection: (body: ChromaConnectionUpdate) =>
    apiRequest<ChromaHealth>("/api/chroma/connection", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  collections: async () => {
    const payload = await apiRequest<{ stores: VectorCollection[] }>("/api/stores");
    return payload.stores || [];
  },
  create: (body: Record<string, unknown>) =>
    apiRequest<VectorCollection>("/api/stores", { method: "POST", body: JSON.stringify(body) }),
  preflight: (body: Record<string, unknown>) =>
    apiRequest<Record<string, unknown>>("/api/stores/preflight/embedding", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  records: (store: string, params: URLSearchParams) =>
    apiRequest<{ records: VectorRecord[]; count: number }>(
      `/api/stores/${encodeURIComponent(store)}/records?${params}`,
    ),
  works: (store: string) =>
    apiRequest<{ works: string[]; stats: VectorWorkStat[] }>(
      `/api/stores/${encodeURIComponent(store)}/works`,
    ),
  search: (store: string, body: Record<string, unknown>, signal?: AbortSignal) =>
    apiRequest<{ results: VectorSearchResult[]; pipeline?: StoreSearchPipelineIdentity }>(
      `/api/stores/${encodeURIComponent(store)}/search`,
      { method: "POST", body: JSON.stringify(body), signal },
    ),
  setLanguages: (store: string, body: { language_codes: string[]; collection_role: string }) =>
    apiRequest<VectorCollection>(`/api/stores/${encodeURIComponent(store)}/languages`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  setEmbedding: (
    store: string,
    body: { embedding_provider: string; embedding_model: string | null },
  ) =>
    apiRequest<VectorCollection>(`/api/stores/${encodeURIComponent(store)}/embedding`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  setProtection: (store: string, protectedFlag: boolean) =>
    apiRequest<VectorCollection>(`/api/stores/${encodeURIComponent(store)}/protection`, {
      method: "PUT",
      body: JSON.stringify({ protected: protectedFlag }),
    }),
  remove: (store: string) =>
    apiRequest<unknown>(`/api/stores/${encodeURIComponent(store)}`, { method: "DELETE" }),
  exportRecords: (store: string, work?: string) => {
    const params = new URLSearchParams();
    if (work) params.set("work", work);
    const query = params.toString();
    return apiRequest<{ records: VectorRecord[] }>(
      `/api/stores/${encodeURIComponent(store)}/export${query ? `?${query}` : ""}`,
    );
  },
  deriveLanguages: (
    store: string,
    body: { en_name: string; fr_name: string; overwrite?: boolean },
  ) =>
    apiRequest<Record<string, unknown>>(
      `/api/stores/${encodeURIComponent(store)}/derive-languages`,
      { method: "POST", body: JSON.stringify(body) },
    ),
};
