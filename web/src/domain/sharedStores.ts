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
import { isResponseCacheStore } from "./recordPayloads";
import { state } from "./sharedUrlState";
import { invalidateShellStatusProjection } from "./shellStatusProjection";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

function recordStores(stores: Any[]): Any[] {
  return stores.filter((store) => !isResponseCacheStore(store));
}

// Reload the vector-store list and keep the active store pointing at a corpus store that still exists.
export async function refreshStores() {
  const data = await api("/api/stores");
  state.stores = data.stores || [];
  state.storesLastFetchedAt = Date.now();
  const corpus = recordStores(state.stores);
  if (state.activeStore && !corpus.some((store) => store.name === state.activeStore))
    state.activeStore = "";
  if (!state.activeStore && corpus.length) state.activeStore = corpus[0].name;
  invalidateShellStatusProjection();
  return state.stores;
}

/** The vector store that holds the Response Library cache, or null when it is not listed. */
export function responseCacheStore() {
  return state.stores.find(isResponseCacheStore) || null;
}
