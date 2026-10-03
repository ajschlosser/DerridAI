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

import { api } from "./legacyApi";
import { state } from "./sharedUrlState";

// The active vector store's record page and the researcher's merged search/browse records, over the shared state.

/** Search hits and the loaded store page as one list keyed by Chroma id (hits win). */
export function researcherDbRecords() {
  const map = new Map();
  for (const item of state.storeSearchResults || []) {
    const record = item.record || {};
    const id = String(item.id || record._chroma_id || record.record_id || "");
    if (id) map.set(id, { ...record, _chroma_id: id });
  }
  for (const record of state.storeRecords || []) {
    const id = String(record._chroma_id || record.record_id || "");
    if (id && !map.has(id)) map.set(id, record);
  }
  return [...map.values()];
}

export async function loadStorePage(): Promise<void> {
  if (!state.activeStore) {
    state.storeRecords = [];
    state.storeCount = 0;
    return;
  }
  const offset = Math.max(0, (state.storePage - 1) * state.storePageSize);
  const params = new URLSearchParams({
    limit: String(state.storePageSize),
    offset: String(offset),
  });
  if (state.storeWork) params.set("work", state.storeWork);
  if (state.storeSort?.key) {
    params.set("sort_field", state.storeSort.key);
    params.set("sort_dir", state.storeSort.dir === -1 ? "desc" : "asc");
  }
  const activeFilters = Object.fromEntries(
    Object.entries(state.storeFilters || {}).filter(([, value]) => String(value || "").trim()),
  );
  if (Object.keys(activeFilters).length) params.set("filters", JSON.stringify(activeFilters));
  const data = await api(`/api/stores/${encodeURIComponent(state.activeStore)}/records?${params}`);
  state.storeRecords = data.records || [];
  state.storeCount = data.count || 0;
  const maxPage = Math.max(1, Math.ceil(state.storeCount / state.storePageSize));
  if (state.storePage > maxPage) {
    state.storePage = maxPage;
    return loadStorePage();
  }
}
