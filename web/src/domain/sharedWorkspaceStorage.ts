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

import { bindJobsState } from "../state/jobsState";
import { bindWorkspaceGroups, sessionState } from "../state/workspaceState";
import { createWorkspaceDb, DB_NAME } from "../services/workspaceDb";
import { createPrefsPersistence } from "./prefsPersistence";
import { createDomainPreferencePersistence } from "./domainPreferencePersistence";

// The browser-local workspace database and the preference save over the shared workspace state, usable without the
// legacy runtime. The runtime uses this same connection and save, so there is one IndexedDB handle and one debounce.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

/** A researcher's workspace is kept in a database of their own. */
export function workspaceDbName(): string {
  const user = sessionState.userContext;
  return user && user.role !== "admin" && user.id ? `${DB_NAME}-researcher-${user.id}` : DB_NAME;
}

export const workspaceDb = createWorkspaceDb(workspaceDbName);

const prefsState = bindJobsState(bindWorkspaceGroups({})) as Loose;

export const { workspacePrefs, persistPrefs, flushWorkspacePrefs } = createPrefsPersistence({
  state: prefsState,
  put: workspaceDb.put,
});

export const {
  persistResearchPreferences,
  persistSearchPreferences,
  persistListPreferences,
  persistLayoutPreferences,
  persistReviewPreferences,
  persistVectorPreferences,
  persistJobPreferences,
  flushDomainPreferences,
  cancelPendingDomainPreferences,
} = createDomainPreferencePersistence({
  state: prefsState,
  put: workspaceDb.put,
});

let shellRefreshHook: () => void = () => {};
/** The shell (sidebar, breadcrumbs, user menu) installs how it refreshes itself. */
export function setShellRefreshHook(hook: unknown) {
  shellRefreshHook = typeof hook === "function" ? (hook as () => void) : () => {};
}
/** Refreshes the shell snapshot without saving the preferences. */
export function refreshShell() {
  shellRefreshHook();
}
/** Saves the preferences and refreshes the shell snapshot. */
export function shell() {
  persistPrefs();
  refreshShell();
}
