/* Copyright 2026 Aaron John Schlosser, PhD. */

import { cloneAuditValue } from "./recordValues";
import { viewConfig } from "./runtimeConstants";
import { compressUrlState, decompressUrlState } from "./urlState";

// Navigation: the browser history, the shareable URL and the link between the URL and the runtime's view state. Moved
// verbatim from the legacy runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "activeFile"
  | "canAccessPage"
  | "dbSearchWhere"
  | "persistPrefs"
  | "renderView"
  | "selectedIndex"
  | "shell";
type Deps = { state: Loose } & Record<Helper, Fn>;

/** The path each view lives at, and the reverse map. */
export const viewPathMap: Record<string, string> = {
  home: "/",
  list: "/records",
  record: "/record",
  works: "/works",
  global: "/search",
  annotations: "/annotations",
  pdf: "/pdf",
  compare: "/compare",
  vector: "/databases",
  rag: "/rag",
  faq: "/faq",
  responsecache: "/system-data",
  providers: "/providers",
  schemas: "/schemas",
  config: "/settings",
};
export const pathViewMap: Record<string, string> = Object.fromEntries(
  Object.entries(viewPathMap).map(([view, path]) => [path, view]),
);

export function createNavigation(deps: Deps) {
  const {
    state,
    activeFile,
    canAccessPage,
    dbSearchWhere,
    persistPrefs,
    renderView,
    selectedIndex,
    shell,
  } = deps;
  let urlSyncHook: Any = null;
  function getUrlSyncHook() {
    return urlSyncHook;
  }
  function viewLabel(view: Any) {
    return viewConfig.find((item: Any) => item.id === view)?.label || view;
  }
  function navSnapshot() {
    const file = activeFile();
    return {
      getUrlSyncHook,
      view: state.view,
      activeFileId: state.activeFileId,
      selectedIndex: file ? selectedIndex(file) : 0,
      activeStore: state.activeStore || "",
      storeWork: state.storeWork || "",
      storePage: state.storePage || 1,
      storeBrowseMode: state.storeBrowseMode || "works",
      pdfPage: state.pdf.page || 1,
      // Breadcrumb back/forward restores the same state that a copied URL does,
      // rather than only restoring the page shell.
      urlState: cloneAuditValue(currentTableUrlState(state.view)),
    };
  }
  function sameSnapshot(a: Any, b: Any) {
    if (!a || !b) return false;
    return JSON.stringify(a) === JSON.stringify(b);
  }
  function applyNavSnapshot(target: Any) {
    if (!target) return;
    if (target.activeFileId && state.files.some((file: Any) => file.id === target.activeFileId))
      state.activeFileId = target.activeFileId;
    state.view = target.view || "home";
    if (state.activeFileId && Number.isFinite(+target.selectedIndex))
      state.selected[state.activeFileId] = +target.selectedIndex;
    if (target.activeStore !== undefined) state.activeStore = target.activeStore || "";
    if (target.storeWork !== undefined) state.storeWork = target.storeWork || "";
    if (Number.isFinite(+target.storePage)) state.storePage = Math.max(1, +target.storePage);
    if (target.storeBrowseMode) state.storeBrowseMode = target.storeBrowseMode;
    if (Number.isFinite(+target.pdfPage)) state.pdf.page = Math.max(1, +target.pdfPage);
    if (target.urlState) applyCompressedTableUrlState(target.urlState, state.view);
  }
  function setUrlSyncHook(hook: Any) {
    urlSyncHook = typeof hook === "function" ? hook : null;
  }
  function currentTableUrlState(view = state.view) {
    // URL state is intentionally view-scoped. It is the public/shareable state
    // contract for a page; IndexedDB remains only a convenience for restoring a
    // user's workspace when no URL overrides are present.
    if (view === "list") {
      const f = activeFile();
      if (!f) return null;
      return {
        c: state.tableColumns.list || null,
        s: state.sorts[f.id] || null,
        f: state.listFilters[f.id] || null,
        p: state.pages[f.id] || 1,
        z: state.pageSize,
        q: state.searches[f.id] || "",
      };
    }
    if (view === "global")
      return {
        c: state.tableColumns.global || null,
        s: state.globalSort,
        f: state.globalFilters,
        sf: state.searchFacetFilters || {},
        p: state.globalPage,
        z: state.pageSize,
        q: state.globalSearch,
        m: state.globalSearchMode,
        dm: state.dbSearchMethod,
        dw: state.dbSearchWhere,
        dk: state.dbSearchFetchK,
        dl: state.dbSearchLambda,
        ao: Boolean(state.globalAdvancedOpen),
        l: state.searchResultLayouts,
      };
    if (view === "vector")
      return {
        c: state.tableColumns.vector || null,
        s: state.storeSort,
        f: state.storeFilters,
        p: state.storePage,
        z: state.storePageSize,
        w: state.storeWork,
        b: state.storeBrowseMode,
        ss: state.storeSearchSort,
        q: state.storeQuery,
      };
    if (view === "works") return { q: state.worksSearch || "", w: state.workOverview || "" };
    if (view === "annotations")
      return { q: state.annotationSearch || "", m: state.annotationView || "works" };
    if (view === "home")
      return {
        m: Number(state.dashboardMetricIndex) || 0,
        sm: state.globalSearchMode || "traditional",
        q: state.globalSearch || "",
      };
    if (view === "record") return { q: state.recordFind || "", rr: state.researcherRecordId || "" };
    if (view === "faq") return { q: state.faqSearch || "", p: state.faqPage || 1 };
    return null;
  }
  function applyCompressedTableUrlState(value: Any, view = state.view) {
    if (!value || typeof value !== "object") return;
    if (view === "list") {
      const f = activeFile();
      if (!f) return;
      if (Array.isArray(value.c)) state.tableColumns.list = value.c;
      if (value.s) state.sorts[f.id] = value.s;
      if (value.f && typeof value.f === "object") state.listFilters[f.id] = value.f;
      if (Number.isFinite(+value.p)) state.pages[f.id] = Math.max(1, +value.p);
      if (Number.isFinite(+value.z)) state.pageSize = Math.max(10, +value.z);
      if (typeof value.q === "string") state.searches[f.id] = value.q;
    } else if (view === "global") {
      if (Array.isArray(value.c)) state.tableColumns.global = value.c;
      if (value.s) state.globalSort = value.s;
      if (Array.isArray(value.f)) state.globalFilters = value.f;
      if (value.sf && typeof value.sf === "object" && !Array.isArray(value.sf))
        state.searchFacetFilters = Object.fromEntries(
          Object.entries(value.sf)
            .map(([field, values]) => [field, Array.isArray(values) ? values.map(String) : []])
            .filter(([, values]) => values.length),
        );
      if (Number.isFinite(+value.p)) state.globalPage = Math.max(1, +value.p);
      if (Number.isFinite(+value.z)) state.pageSize = Math.max(10, +value.z);
      if (typeof value.q === "string") state.globalSearch = value.q;
      if (["traditional", "database"].includes(value.m)) state.globalSearchMode = value.m;
      if (["similarity", "mmr", "filter"].includes(value.dm)) state.dbSearchMethod = value.dm;
      if (value.dw && typeof value.dw === "object" && !Array.isArray(value.dw))
        state.dbSearchWhere = value.dw;
      if (Number.isFinite(+value.dk)) state.dbSearchFetchK = Math.max(1, +value.dk);
      if (Number.isFinite(+value.dl)) state.dbSearchLambda = Math.max(0, Math.min(1, +value.dl));
      if (typeof value.ao === "boolean") state.globalAdvancedOpen = value.ao;
      if (value.l && typeof value.l === "object")
        state.searchResultLayouts = { ...state.searchResultLayouts, ...value.l };
      if (
        state.globalSearchMode === "database" &&
        (state.globalSearch || Object.keys(dbSearchWhere()).length)
      )
        state.globalSearchAutoRun = true;
    } else if (view === "vector") {
      if (Array.isArray(value.c)) state.tableColumns.vector = value.c;
      if (value.s) state.storeSort = value.s;
      if (value.f && typeof value.f === "object") state.storeFilters = value.f;
      if (Number.isFinite(+value.p)) state.storePage = Math.max(1, +value.p);
      if (Number.isFinite(+value.z)) state.storePageSize = Math.max(10, +value.z);
      if (typeof value.w === "string") state.storeWork = value.w;
      if (["works", "records"].includes(value.b)) state.storeBrowseMode = value.b;
      if (value.ss) state.storeSearchSort = value.ss;
      if (typeof value.q === "string") state.storeQuery = value.q;
    } else if (view === "works") {
      if (typeof value.q === "string") state.worksSearch = value.q;
      if (typeof value.w === "string") state.workOverview = value.w;
    } else if (view === "annotations") {
      if (typeof value.q === "string") state.annotationSearch = value.q;
      if (["works", "recent"].includes(value.m)) state.annotationView = value.m;
    } else if (view === "home") {
      if (Number.isFinite(+value.m)) state.dashboardMetricIndex = Math.max(0, +value.m);
      if (["traditional", "database"].includes(value.sm)) state.globalSearchMode = value.sm;
      if (typeof value.q === "string") state.globalSearch = value.q;
    } else if (view === "record") {
      if (typeof value.q === "string") state.recordFind = value.q;
      if (typeof value.rr === "string") state.researcherRecordId = value.rr;
    } else if (view === "faq") {
      if (typeof value.q === "string") state.faqSearch = value.q;
      if (Number.isFinite(+value.p)) state.faqPage = Math.max(1, +value.p);
    }
  }
  function urlFromState() {
    const url = new URL(location.href);
    const params = url.searchParams;
    for (const key of [
      "view",
      "file",
      "record",
      "store",
      "work",
      "dbpage",
      "browse",
      "pdfpage",
      "ts",
    ])
      params.delete(key);
    params.set("view", state.view || "home");
    if (state.activeFileId) params.set("file", state.activeFileId);
    const file = activeFile();
    if (file && Number.isFinite(selectedIndex(file)))
      params.set("record", String(selectedIndex(file)));
    if (state.activeStore) params.set("store", state.activeStore);
    if (state.storeWork) params.set("work", state.storeWork);
    if (state.storePage > 1) params.set("dbpage", String(state.storePage));
    if (state.storeBrowseMode && state.storeBrowseMode !== "works")
      params.set("browse", state.storeBrowseMode);
    if (state.view === "pdf" && state.pdf.page > 1) params.set("pdfpage", String(state.pdf.page));
    const tableState = currentTableUrlState();
    if (tableState) {
      const compressed = compressUrlState(tableState);
      if (compressed) params.set("ts", compressed);
    }
    const path = viewPathMap[state.view] || "/";
    const query = params.toString();
    return `${path}${query ? `?${query}` : ""}${url.hash}`;
  }
  function syncUrl({ replace = false, href = null }: Any = {}) {
    href = href || urlFromState();
    const current = `${location.pathname}${location.search}${location.hash}`;
    if (href === current) return;
    const snapshot = navSnapshot();
    if (urlSyncHook) {
      urlSyncHook(href, { replace, snapshot });
      return;
    }
    try {
      history[replace ? "replaceState" : "pushState"](snapshot, "", href);
    } catch (error) {
      console.warn("Could not update browser URL state", error);
    }
  }
  function applyUrlState() {
    const params = new URLSearchParams(location.search);
    const pathView = pathViewMap[location.pathname];
    const view = pathView || params.get("view");
    if (view && viewConfig.some((item: Any) => item.id === view)) state.view = view;
    const file = params.get("file");
    // A file parameter is authoritative. If the referenced browser-local JSONL
    // is not loaded yet, show the corpus-workspace CTA instead of silently
    // substituting another file from IndexedDB. Once the same content is loaded,
    // its stable content-derived id lets the rest of the URL state apply.
    if (file) state.activeFileId = state.files.some((item: Any) => item.id === file) ? file : null;
    const record = Number(params.get("record"));
    if (state.activeFileId && Number.isInteger(record) && record >= 0)
      state.selected[state.activeFileId] = record;
    const store = params.get("store");
    if (store) state.activeStore = store;
    const work = params.get("work");
    if (work !== null) state.storeWork = work;
    const dbPage = Number(params.get("dbpage"));
    if (Number.isFinite(dbPage) && dbPage > 0) state.storePage = dbPage;
    const browse = params.get("browse");
    if (["works", "records"].includes(browse as string)) state.storeBrowseMode = browse;
    const pdfPage = Number(params.get("pdfpage"));
    if (Number.isFinite(pdfPage) && pdfPage > 0) state.pdf.page = pdfPage;
    const compressed = params.get("ts");
    if (compressed) applyCompressedTableUrlState(decompressUrlState(compressed));
  }
  function navigateTo(
    view: Any,
    {
      fileId = null,
      index = null,
      push = true,
      href = null,
    }: { fileId?: Any; index?: Any; push?: boolean; href?: Any } = {},
  ) {
    if (!canAccessPage(view)) view = "home";
    // Research performs an authoritative store refresh on entry. Do not redirect
    // from this legacy navigation bridge using the cached hasCorpusDb() value; a
    // newly created/restored collection may not have reached shell state yet.
    const before = navSnapshot();
    if (push) {
      const last = state.navHistory[state.navHistory.length - 1];
      if (!sameSnapshot(last, before)) {
        state.navHistory.push(before);
        if (state.navHistory.length > 50) state.navHistory.shift();
      }
      state.navForward = [];
    }
    if (fileId && state.files.some((file: Any) => file.id === fileId)) state.activeFileId = fileId;
    if (index !== null && state.activeFileId) state.selected[state.activeFileId] = Number(index);
    if (state.view === "vector" && view !== "vector") {
      // Store pages/search results duplicate records already persisted in Chroma.
      // Drop those transient copies when leaving Vector Stores.
      state.storeRecords = [];
      state.storeSearchResults = [];
    }
    state.view = view;
    persistPrefs();
    syncUrl({ replace: !push, href });
    shell();
    renderView();
  }
  function goBack() {
    while (state.navHistory.length) {
      const target = state.navHistory.pop();
      if (!target) continue;
      if (target.activeFileId && !state.files.some((file: Any) => file.id === target.activeFileId))
        continue;
      state.navForward.push(navSnapshot());
      if (state.navForward.length > 50) state.navForward.shift();
      applyNavSnapshot(target);
      persistPrefs();
      syncUrl({ replace: true });
      shell();
      renderView();
      return;
    }
  }
  function goForward() {
    while (state.navForward.length) {
      const target = state.navForward.pop();
      if (!target) continue;
      if (target.activeFileId && !state.files.some((file: Any) => file.id === target.activeFileId))
        continue;
      state.navHistory.push(navSnapshot());
      applyNavSnapshot(target);
      persistPrefs();
      syncUrl({ replace: true });
      shell();
      renderView();
      return;
    }
  }
  return {
    viewLabel,
    navSnapshot,
    sameSnapshot,
    applyNavSnapshot,
    setUrlSyncHook,
    currentTableUrlState,
    applyCompressedTableUrlState,
    urlFromState,
    syncUrl,
    applyUrlState,
    navigateTo,
    goBack,
    goForward,
  };
}
