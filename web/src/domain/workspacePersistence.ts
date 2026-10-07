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
  restorePreferenceOverlays?: () => Promise<void>;
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
    restorePreferenceOverlays,
  } = deps;
  const pendingFiles = new Map<string, Any>();

  async function writeFileNow(file: Any) {
    try {
      await idbPut("files", serializableFile(file));
    } catch (error: Any) {
      console.error("IndexedDB file persistence failed", error);
      toast(trf("runtime.toast.persistence_failed", { detail: error.message }), { tone: "danger" });
    }
  }

  /**
   * Persists an already-mutated file without invalidating corpus projections.
   *
   * Mutation owners invalidate exactly once when they change Records. Keeping
   * storage I/O pure prevents a debounced save from causing a second/third
   * corpus refresh after the user's edit already rendered.
   */
  async function persistFileNow(file: Any) {
    const id = String(file?.id || "");
    if (id) {
      const timer = fileTimers.get(id);
      if (timer) clearTimeout(timer);
      fileTimers.delete(id);
      pendingFiles.delete(id);
    }
    await writeFileNow(file);
  }

  function persistFile(file: Any) {
    const id = String(file?.id || "");
    if (!id) return;
    pendingFiles.set(id, file);
    clearTimeout(fileTimers.get(id));
    const timer = setTimeout(() => {
      fileTimers.delete(id);
      const pending = pendingFiles.get(id);
      pendingFiles.delete(id);
      if (pending) void writeFileNow(pending);
    }, 250);
    fileTimers.set(id, timer);
  }

  async function flushPendingFileWrites() {
    const pending = [...pendingFiles.entries()];
    for (const [id] of pending) {
      const timer = fileTimers.get(id);
      if (timer) clearTimeout(timer);
      fileTimers.delete(id);
    }
    pendingFiles.clear();
    for (const [, file] of pending) await writeFileNow(file);
  }

  function cancelPendingFileWrites() {
    for (const timer of fileTimers.values()) clearTimeout(timer);
    fileTimers.clear();
    pendingFiles.clear();
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
      invalidateCorpusCache(null, true);
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
        state.llmConfig = { ...preservedLlmDefaults, ...(prefs.llmConfig || {}) };
        state.ragConfig = { ...state.ragConfig, ...(prefs.ragConfig || {}) };
        if (Number.isFinite(+prefs.pageSize)) state.pageSize = +prefs.pageSize;
        if (typeof prefs.view === "string") state.view = prefs.view;
        state.reviewSelection = new Set(prefs.reviewSelection || []);
        state.activeFileId = state.files.some((f: Any) => f.id === prefs.activeFileId)
          ? prefs.activeFileId
          : state.files[0]?.id || null;
      } else {
        state.activeFileId = state.files[0]?.id || null;
        try {
          state.appConfig.ui_color_theme =
            localStorage.getItem("derridai.ui.theme") || state.appConfig.ui_color_theme || "green";
        } catch {
          // Best effort: keep going with what we have.
        }
      }

      // Domain records are the authoritative post-migration preferences. Apply
      // them before final validation/theme/provider setup and before storage is
      // marked ready, so no watcher can persist legacy fallback values over
      // newer domain-owned state during startup.
      if (restorePreferenceOverlays) await restorePreferenceOverlays();

      // The corpus-domain record may come from an older workspace snapshot or
      // from a file that was deleted independently. Never leave the restored
      // workspace pointing at a tab that does not exist.
      state.activeFileId = state.files.some((file: Any) => file.id === state.activeFileId)
        ? state.activeFileId
        : state.files[0]?.id || null;

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
      if (!Number.isFinite(+state.pageSize)) state.pageSize = 100;
      ensureProviderProfiles();
      applyUiTheme(state.appConfig.ui_color_theme);

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
    flushPendingFileWrites,
    cancelPendingFileWrites,
    restoreWorkspace,
  };
}
