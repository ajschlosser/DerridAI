/* Copyright 2026 Aaron John Schlosser, PhD. */

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
  | "toast";
type Deps = {
  state: Loose;
  fileTimers: Map<string, ReturnType<typeof setTimeout>>;
} & Record<Helper, Fn>;

let prefsTimer: Any = null;
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
    toast,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  async function persistFileNow(file: Any) {
    invalidateCorpusCache();
    try {
      await idbPut("files", serializableFile(file));
    } catch (error: Any) {
      console.error("IndexedDB file persistence failed", error);
      toast(`Local persistence failed: ${error.message}`);
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
    return {
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
      navHistory: state.navHistory,
      navForward: state.navForward,
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
  }
  function persistPrefs() {
    if (!state.storageReady) return;
    clearTimeout(prefsTimer);
    prefsTimer = setTimeout(
      () =>
        idbPut("prefs", workspacePrefs()).catch((error: Any) =>
          console.error("IndexedDB preference persistence failed", error),
        ),
      400,
    );
  }
  async function flushWorkspacePrefs() {
    if (!state.storageReady) throw new Error("Workspace storage is not ready yet.");
    clearTimeout(prefsTimer);
    await idbPut("prefs", workspacePrefs());
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
          "navHistory",
          "navForward",
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
      toast(`Could not restore saved workspace: ${error.message}`);
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
