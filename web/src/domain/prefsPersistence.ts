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

// Saving the workspace preferences to IndexedDB, debounced. Moved out of the workspace persistence factory so it needs
// only the shared workspace state and a `put`, and so Vue code can persist without the legacy runtime.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any

let prefsTimer: Any = null;

/** Drops a pending debounced save, for example before the workspace database is deleted. */
export function cancelPendingPrefs() {
  clearTimeout(prefsTimer);
  prefsTimer = null;
}

export function createPrefsPersistence(deps: {
  state: Loose;
  put: (storeName: string, value: unknown) => Promise<void>;
}) {
  const { state, put } = deps;
  function workspacePrefs() {
    const cloneable = (value: Any): Any => {
      if (value === null || ["string", "number", "boolean"].includes(typeof value)) return value;
      if (value instanceof Date) return value.toISOString();
      if (value instanceof Set) return [...value].map(cloneable);
      if (Array.isArray(value)) return value.map(cloneable).filter((item) => item !== undefined);
      if (typeof value === "object") {
        return Object.fromEntries(
          Object.entries(value)
            .filter(([, item]) => typeof item !== "function" && item !== undefined)
            .map(([key, item]) => [key, cloneable(item)]),
        );
      }
      return undefined;
    };
    const prefs = {
      key: "workspace",
      activeFileId: state.activeFileId,
      view: state.view,
      selected: state.selected,
      searches: state.searches,
      listFilters: state.listFilters,
      pages: state.pages,
      pageSize: state.pageSize,
      sorts: state.sorts,
      globalSearch: state.globalSearch,
      globalFilters: state.globalFilters,
      globalSort: state.globalSort,
      globalPage: state.globalPage,
      globalSearchMode: state.globalSearchMode,
      dbSearchMethod: state.dbSearchMethod,
      dbSearchWhere: state.dbSearchWhere,
      dbSearchFetchK: state.dbSearchFetchK,
      dbSearchLambda: state.dbSearchLambda,
      globalAdvancedOpen: state.globalAdvancedOpen,
      searchFacetFilters: state.searchFacetFilters,
      worksSearch: state.worksSearch,
      workOverview: state.workOverview,
      worksSort: state.worksSort,
      worksNeedsReview: state.worksNeedsReview,
      worksDbStatus: state.worksDbStatus,
      worksAuthor: state.worksAuthor,
      worksView: state.worksView,
      researcherRecordId: state.researcherRecordId,
      researcherCompareA: state.researcherCompareA,
      researcherCompareB: state.researcherCompareB,
      dashboardMetricIndex: state.dashboardMetricIndex,
      lastViewedRecord: state.lastViewedRecord,
      compareA: state.compareA,
      compareB: state.compareB,
      compareMode: state.compareMode,
      comparePasteA: state.comparePasteA,
      comparePasteB: state.comparePasteB,
      compareSourceA: state.compareSourceA,
      compareSourceB: state.compareSourceB,
      compareFilter: state.compareFilter,
      activeStore: state.activeStore,
      storePage: state.storePage,
      storePageSize: state.storePageSize,
      storeQuery: state.storeQuery,
      storeSearchMode: state.storeSearchMode,
      storeWork: state.storeWork,
      storeSort: state.storeSort,
      storeFilters: state.storeFilters,
      storeBrowseMode: state.storeBrowseMode,
      vectorTab: state.vectorTab,
      vectorCollectionFilter: state.vectorCollectionFilter,
      llmConfig: state.llmConfig,
      appConfig: cloneable(state.appConfig),
      ragConfig: cloneable(state.ragConfig),
      faqSearch: state.faqSearch,
      faqPage: state.faqPage,
      faqExpanded: state.faqExpanded,
      sidebarCollapsed: state.sidebarCollapsed,
      collectionsCollapsed: state.collectionsCollapsed,
      operationToastsMinimized: state.operationToastsMinimized,
      operationStackPosition: state.operationStackPosition,
      collapsedPanels: state.collapsedPanels,
      tableColumns: state.tableColumns,
      upsertState: state.upsertState,
      upsertIgnored: state.upsertIgnored,
      jobApplied: state.jobApplied,
      upsertJobApplied: state.upsertJobApplied,
      reviewSelection: [...state.reviewSelection],
      selectedEvidence: state.selectedEvidence,
      storeSearchSort: state.storeSearchSort,
    };
    // Settings saves use IndexedDB's structured-clone algorithm. Sanitize the
    // complete payload, not just provider config, because shared Vue/runtime
    // state can contain reactive objects or callbacks added by a workspace.
    return cloneable(prefs);
  }
  function persistPrefs() {
    if (!state.storageReady) return;
    clearTimeout(prefsTimer);
    prefsTimer = setTimeout(
      () =>
        put("prefs", workspacePrefs()).catch((error: Any) =>
          console.error("IndexedDB preference persistence failed", error),
        ),
      400,
    );
  }
  async function flushWorkspacePrefs() {
    if (!state.storageReady) throw new Error("Workspace storage is not ready yet.");
    clearTimeout(prefsTimer);
    await put("prefs", workspacePrefs());
  }
  return { workspacePrefs, persistPrefs, flushWorkspacePrefs };
}
