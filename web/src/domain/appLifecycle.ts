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

// Application lifecycle: warming up an LLM provider, and the health check run at
// start-up and after Chroma becomes available. Moved verbatim from the legacy runtime; the runtime's state object and
// helpers are passed in as dependencies.

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "api"
  | "defaultProviderProfile"
  | "ensureProviderProfiles"
  | "isResearcher"
  | "persistPrefs"
  | "warmupProviderProfile"
  | "refreshProviderStatuses"
  | "refreshStoreWorks"
  | "refreshStores"
  | "renderView"
  | "shell"
  | "updateSystemCard";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createAppLifecycle(deps: Deps) {
  const {
    state,
    api,
    defaultProviderProfile,
    ensureProviderProfiles,
    isResearcher,
    persistPrefs,
    warmupProviderProfile,
    refreshProviderStatuses,
    refreshStoreWorks,
    refreshStores,
    renderView,
    shell,
    updateSystemCard,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  async function warmupConfiguredLlm() {
    return warmupProviderProfile(state.appConfig.default_provider_profile);
  }
  async function checkHealth() {
    try {
      state.health = await api("/api/health");
      ensureProviderProfiles();
      await refreshProviderStatuses();
    } catch (error: Any) {
      state.health = { ok: false, error: error.message };
      state.providerStatuses = {};
      state.llmStatus = {
        provider: defaultProviderProfile()?.type || "ollama",
        available: false,
        models: [],
        error: error.message,
      };
    }
    updateSystemCard();
    if (state.health?.chroma?.available) {
      try {
        await refreshStores();
        if (isResearcher() && state.activeStore) await refreshStoreWorks(true);
        const active = document.activeElement;
        const userIsEditing =
          active &&
          active !== document.body &&
          ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName);
        if (userIsEditing) persistPrefs();
        else {
          shell();
          renderView();
        }
      } catch (error: Any) {
        console.warn("Initial Chroma collection refresh failed", error);
      }
    }
  }
  return { warmupConfiguredLlm, checkHealth };
}
