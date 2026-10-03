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

import { toast } from "../composables/notifications";
import { createPrefsPersistence } from "./prefsPersistence";

// Workspace persistence: saving files and preferences to IndexedDB, debounced, and restoring them at start-up. Moved
// verbatim from the legacy runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "applyUiTheme"
  | "ensureProviderProfiles"
  | "idbGet"
  | "idbGetAll"
  | "idbPut"
  | "invalidateCorpusCache"
  | "restoreCurrentPdfAsset"
  | "serializableFile"
  | "trf";
type Deps = {
  state: Loose;
  fileTimers: Map<string, ReturnType<typeof setTimeout>>;
} & Record<Helper, Fn>;

export function createWorkspacePersistence(deps: Deps) {
  const {
    fileTimers,
    state,
    applyUiTheme,
    ensureProviderProfiles,
    idbGet,
    idbGetAll,
    idbPut,
    invalidateCorpusCache,
    restoreCurrentPdfAsset,
    serializableFile,
    trf,
  } = deps;
  const { workspacePrefs, persistPrefs, flushWorkspacePrefs } = createPrefsPersistence({
    state,
    put: (key, value) => idbPut(key, value),
  });
  // The legacy code queries the page freely; untyped, as it was written.
  async function persistFileNow(file: Any) {
    invalidateCorpusCache();
    try {
      await idbPut("files", serializableFile(file));
    } catch (error: Any) {
      console.error("IndexedDB file persistence failed", error);
      toast(trf("runtime.toast.persistence_failed", { detail: error.message }), { tone: "danger" });
    }
  }
  function persistFile(file: Any) {
    invalidateCorpusCache();
    clearTimeout(fileTimers.get(file.id));
    const timer = setTimeout(() => {
      fileTimers.delete(file.id);
      persistFileNow(file);
    }, 250);
    fileTimers.set(file.id, timer);
  }
  async function restoreWorkspace() {
    try {
      const [savedFiles, prefs] = await Promise.all([
        idbGetAll("files"),
        idbGet("prefs", "workspace"),
      ]);
      state.files = (savedFiles || []).map((file: Any) => ({
        ...file,
        dirty: new Set(file.dirty || []),
        errors: file.errors || [],
      }));
      // getShellSnapshot/workIndex can be queried before IndexedDB restore finishes.
      // Always drop derived corpus indexes after reattaching persisted files so the
      // Works page and corpus metrics cannot remain stuck on a cached empty corpus.
      invalidateCorpusCache();
      if (prefs) {
        const preservedAppDefaults = { ...state.appConfig };
        const preservedLlmDefaults = { ...state.llmConfig };
        for (const key of [
          "selected",
          "searches",
          "listFilters",
          "pages",
          "sorts",
          "globalSearch",
          "globalFilters",
          "globalSort",
          "globalPage",
          "globalSearchMode",
          "globalSearchAutoRun",
          "searchResultLayouts",
          "dbSearchMethod",
          "dbSearchWhere",
          "dbSearchFetchK",
          "dbSearchLambda",
          "globalAdvancedOpen",
          "searchFacetFilters",
          "worksSearch",
          "workOverview",
          "worksSort",
          "worksNeedsReview",
          "worksDbStatus",
          "worksAuthor",
          "worksView",
          "researcherRecordId",
          "researcherCompareA",
          "researcherCompareB",
          "dashboardMetricIndex",
          "lastViewedRecord",
          "compareA",
          "compareB",
          "compareMode",
          "comparePasteA",
          "comparePasteB",
          "compareSourceA",
          "compareSourceB",
          "compareFilter",
          "faqSearch",
          "faqPage",
          "faqExpanded",
          "activeStore",
          "storePage",
          "storePageSize",
          "storeQuery",
          "storeSearchMode",
          "storeWork",
          "storeSort",
          "storeFilters",
          "storeBrowseMode",
          "vectorTab",
          "vectorCollectionFilter",
          "storeSearchSort",
          "selectedEvidence",
          "sidebarCollapsed",
          "collectionsCollapsed",
          "operationToastsMinimized",
          "operationStackPosition",
          "collapsedPanels",
          "tableColumns",
          "upsertState",
          "upsertIgnored",
          "jobApplied",
          "upsertJobApplied",
        ]) {
          if (prefs[key] !== undefined) state[key] = prefs[key];
        }
        state.appConfig = { ...preservedAppDefaults, ...(prefs.appConfig || {}) };
        applyUiTheme(state.appConfig.ui_color_theme);
        state.llmConfig = { ...preservedLlmDefaults, ...(prefs.llmConfig || {}) };
        state.ragConfig = { ...state.ragConfig, ...(prefs.ragConfig || {}) };
        if (
          !state.faqExpanded ||
          typeof state.faqExpanded !== "object" ||
          Array.isArray(state.faqExpanded)
        )
          state.faqExpanded = {};
        state.ragConfig.locales = Array.isArray(state.ragConfig.locales)
          ? state.ragConfig.locales.filter((value: Any) => value === "en" || value === "fr")
          : ["en", "fr"];
        if (!state.ragConfig.locales.length) state.ragConfig.locales = ["en", "fr"];
        state.ragConfig.prompt = String(state.ragConfig.prompt || "");
        state.ragConfig.instructions = String(state.ragConfig.instructions || "");
        if (!Array.isArray(state.ragConfig.history)) state.ragConfig.history = [];
        state.ragConfig.history = state.ragConfig.history.slice(0, 100);
        if (!Array.isArray(state.ragConfig.run_history)) state.ragConfig.run_history = [];
        state.ragConfig.run_history = state.ragConfig.run_history.slice(0, 250);
        if (!state.appConfig.default_review_preset) state.appConfig.default_review_preset = "text";
        if (!state.appConfig.default_llm_run_mode)
          state.appConfig.default_llm_run_mode = "foreground";
        ensureProviderProfiles();
        if (Number.isFinite(+prefs.pageSize)) state.pageSize = +prefs.pageSize;
        if (typeof prefs.view === "string") state.view = prefs.view;
        state.reviewSelection = new Set(prefs.reviewSelection || []);
        state.activeFileId = state.files.some((f: Any) => f.id === prefs.activeFileId)
          ? prefs.activeFileId
          : state.files[0]?.id || null;
      } else {
        state.activeFileId = state.files[0]?.id || null;
        ensureProviderProfiles();
        try {
          state.appConfig.ui_color_theme =
            localStorage.getItem("derridai.ui.theme") || state.appConfig.ui_color_theme || "green";
        } catch {
          // Best effort: keep going with what we have.
        }
        applyUiTheme(state.appConfig.ui_color_theme);
      }
      const validPrefixes = new Set(state.files.map((f: Any) => f.id));
      state.reviewSelection = new Set(
        [...state.reviewSelection].filter((key) => validPrefixes.has(String(key).split("::")[0])),
      );
      await restoreCurrentPdfAsset();
    } catch (error: Any) {
      console.error("Could not restore IndexedDB workspace", error);
      toast(trf("runtime.toast.workspace_restore_failed", { detail: error.message }), {
        tone: "danger",
      });
    } finally {
      state.storageReady = true;
    }
  }
  return {
    persistFileNow,
    persistFile,
    workspacePrefs,
    persistPrefs,
    flushWorkspacePrefs,
    restoreWorkspace,
  };
}
