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

/** Loads the works of the active store into the shared state; `force` reloads when the store is unchanged. */
export async function refreshStoreWorks(force = false): Promise<void> {
  if (!state.activeStore) {
    state.storeWorks = [];
    state.storeWorkStats = [];
    state.storeWorksStore = "";
    state.storeWork = "";
    return;
  }
  if (!force && state.storeWorksStore === state.activeStore) return;
  const data = await api(`/api/stores/${encodeURIComponent(state.activeStore)}/works`);
  state.storeWorks = data.works || [];
  state.storeWorkStats =
    data.stats || state.storeWorks.map((work: string) => ({ work, count: null }));
  state.storeWorksStore = state.activeStore;
  if (state.storeWork && !state.storeWorks.includes(state.storeWork)) state.storeWork = "";
}
