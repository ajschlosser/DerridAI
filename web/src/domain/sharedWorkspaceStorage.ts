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

/**
 * Every authenticated account gets its own browser-local workspace.
 *
 * The old implementation only namespaced researcher databases. Two
 * administrators using the same browser profile therefore reopened the same
 * IndexedDB corpus, provider settings, and evidence state after an account
 * switch. The in-memory session reset cannot provide isolation if restore then
 * reads the previous administrator's database again.
 */
export function workspaceDbName(): string {
  const user = sessionState.userContext;
  if (!user?.id) return DB_NAME;
  const role = String(user.role || "user").replace(/[^a-z0-9_-]+/gi, "-");
  return `${DB_NAME}-${role}-${String(user.id)}`;
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
  persistSettingsPreferences,
  persistAnnotationsPreferences,
  persistCorpusPreferences,
  persistWorksPreferences,
  persistRecordViewPreferences,
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
/**
 * Refreshes the shell snapshot.
 *
 * Durable state is persisted by the feature/domain that owns the mutation.
 * Keeping shell rendering side-effect free is critical: otherwise every record
 * edit, navigation, health refresh, and background-job update serializes the
 * entire compatibility workspace merely because chrome needs repainting.
 */
export function shell() {
  refreshShell();
}
