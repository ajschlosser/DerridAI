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

import { state } from "./sharedUrlState";
import { syncUrl } from "./sharedNavigation";
import { persistPrefs } from "./sharedWorkspaceStorage";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function pageInfo(total: number, page?: number) {
  const pages = Math.max(1, Math.ceil(total / state.pageSize));
  page = Math.max(1, Math.min(pages, page || 1));
  return {
    page,
    pages,
    start: (page - 1) * state.pageSize,
    end: Math.min(total, page * state.pageSize),
  };
}

export function setListFilterValue(fileId: string, key: string, value: unknown) {
  if (!(state.listFilters as Any)[fileId]) (state.listFilters as Any)[fileId] = {};
  if (value === "" || value == null) delete (state.listFilters as Any)[fileId][key];
  else (state.listFilters as Any)[fileId][key] = value;
  persistPrefs();
}

export function setActiveStore(name?: string) {
  const next = name || "";
  if (state.activeStore !== next) {
    state.storeWorksStore = "";
    // Presence maps can become very large for corpus-scale workspaces. Keep
    // only the selected store's map when switching collections.
    state.storePresence =
      next && state.storePresence?.[next] ? { [next]: state.storePresence[next] } : {};
    state.storePresenceIds =
      next && state.storePresenceIds?.[next] ? { [next]: state.storePresenceIds[next] } : {};
    state.storePresenceCheckedAt =
      next && state.storePresenceCheckedAt?.[next]
        ? { [next]: state.storePresenceCheckedAt[next] }
        : {};
  }
  state.activeStore = next;
  persistPrefs();
  syncUrl({ replace: true });
}
