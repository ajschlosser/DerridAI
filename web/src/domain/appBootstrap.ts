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

// Start-up and session entry points `App.vue` calls: sign-in context, location re-sync and the one-time bootstrap.
import "../runtime/registrations.js";
import { refreshResearcherContentPolicy } from "./researcherInputFilter";
import { wireTabScrollPreservation } from "./tabScrollPreservation";
import { wireMetadataSearchDelegation } from "./legacyDomListeners";
import { api } from "./legacyApi";
import { refreshJobs, startJobPolling, startRealtime } from "./jobsActions";
import { applyUrlState, renderView, repaintAfterLocationChange } from "./sharedNavigation";
import { applyAppearance } from "./sharedAppearance";
import { canAccessPage, isResearcher } from "./sharedSession";
import { state } from "./sharedUrlState";
import { restoreWorkspace } from "./sharedWorkspacePersistence";
import { checkHealth, warmupConfiguredLlm } from "./sharedAppLifecycle";
import { shell } from "./sharedWorkspaceStorage";

export { setUrlSyncHook } from "./sharedNavigation";
export { setShellRefreshHook } from "./sharedWorkspaceStorage";

export function setUserContext(user: { id?: string | number } | null) {
  const priorId = state.userContext?.id;
  state.userContext = user || null;
  if (priorId !== state.userContext?.id) {
    state.serverAnnotations = [];
    state.serverAnnotationsStore = "";
    state.annotationsFetchedAt = 0;
  }
  if (!canAccessPage(state.view)) state.view = "home";
  void refreshResearcherContentPolicy();
}

// Names of the facts shown for an operation (panel rows and the details dialog), translated at render time.

// ---- Operations panel bridge -------------------------------------------------------------
// The panel itself is a Vue component (components/OperationsPanel.vue). The runtime still owns
// job state, the dock, toasts, and the details/results dialogs, so the panel reads a plain view
// model from here and calls back into the existing functions.

// 0.36.10 native Search bridge. SearchView owns presentation while the runtime
// continues to own browser-local corpus state, Chroma transport, evidence
// selection, URL serialization, and the existing LLM review workflows.

/**
 * Re-derive runtime view state from the browser location (the router owns the URL) and repaint.
 * Used by browser back/forward and whenever a router navigation settles somewhere the runtime did not expect.
 */
export function syncFromLocation() {
  applyUrlState();
  repaintAfterLocationChange();
}

export async function bootstrapRuntime() {
  wireTabScrollPreservation();
  wireMetadataSearchDelegation();
  await restoreWorkspace();
  try {
    if (!state.appConfig.ui_color_scheme)
      state.appConfig.ui_color_scheme = localStorage.getItem("derridai.ui.scheme") || "system";
    if (!state.appConfig.ui_contrast)
      state.appConfig.ui_contrast = localStorage.getItem("derridai.ui.contrast") || "system";
  } catch {
    /* localStorage can be blocked */
  }
  applyAppearance({
    ui_color_theme: state.appConfig.ui_color_theme,
    ui_color_scheme: state.appConfig.ui_color_scheme || "system",
    ui_contrast: state.appConfig.ui_contrast || "system",
  });
  try {
    const providerData: { profiles?: unknown } = await api("/api/system/researcher-providers");
    state.researcherProviderProfiles = Array.isArray(providerData.profiles)
      ? providerData.profiles
      : [];
  } catch (error) {
    console.warn("Could not load researcher provider profiles", error);
    state.researcherProviderProfiles = [];
  }
  if (isResearcher()) {
    state.files = [];
    state.activeFileId = null;
    state.selected = {};
    state.reviewSelection = new Set();
    if (
      ![
        "home",
        "rag",
        "vector",
        "works",
        "global",
        "record",
        "compare",
        "annotations",
        "semanticmap",
        "config",
      ].includes(state.view)
    )
      state.view = "home";
  }
  applyUrlState();
  if (!canAccessPage(state.view)) state.view = "home";
  shell();
  // A native Vue route may be active without #main. In that case bootstrap
  // background health/job state only; the mounted view owns #main and its own render.
  if (document.querySelector("#main")) renderView();
  await checkHealth();
  // One discovery request on startup is not a polling loop. Afterwards job state
  // follows the realtime socket; REST polling runs only as a fallback while the
  // socket is unavailable (docs/REALTIME.md).
  await refreshJobs({ rerender: false });
  startRealtime();
  startJobPolling();
  if (!isResearcher() && state.appConfig.warm_default_provider_on_start === true)
    warmupConfiguredLlm();
}

// 0.31.0 native Research bridge. The Vue Research workspace owns presentation,
// while this compatibility layer continues to own corpus/provider/job state and
// the sparse API contracts introduced in 0.30.11. Keep the bridge intentionally
// operation-specific so native components never need to receive credentials,
// full corpus records, or unrelated runtime state.

// 0.35.10 — Record Player. The Record page is Vue-native; this bridge exposes
// only the current record data and actions needed by that workspace. Audit
// history is summarized separately so the heavyweight `updates` payload never
// becomes ordinary component state.
