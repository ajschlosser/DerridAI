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

import { WORKS_DB_STATUSES, WORKS_SORTS } from "./worksWorkspace";
import { viewConfig } from "./runtimeConstants";
import { compressUrlState, decompressUrlState } from "./urlState";
import { viewFromPath, viewPathMap } from "./viewPaths";

// The shareable-URL contract: which parts of the workspace state a URL carries and how a URL is applied back. Split out
// of navigation.ts so it depends only on the state and three read helpers, not on rendering or history.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

type Helper = "activeFile" | "dbSearchWhere" | "selectedIndex";
export type UrlStateCodecDeps = { state: Loose } & Record<Helper, Fn>;

export function createUrlStateCodec(deps: UrlStateCodecDeps) {
  const { state, activeFile, dbSearchWhere, selectedIndex } = deps;
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
    if (view === "works")
      return {
        q: state.worksSearch || "",
        w: state.workOverview || "",
        s: state.worksSort || "title-asc",
        r: Boolean(state.worksNeedsReview),
        d: state.worksDbStatus || "",
        a: state.worksAuthor || "",
        v: state.worksView || "cards",
      };
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
      state.worksSort = WORKS_SORTS.includes(value.s) ? value.s : "title-asc";
      state.worksNeedsReview = value.r === true;
      state.worksDbStatus = WORKS_DB_STATUSES.includes(value.d) ? value.d : "";
      state.worksAuthor = typeof value.a === "string" ? value.a : "";
      state.worksView = ["list", "compact"].includes(value.v) ? "list" : "cards";
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
  function urlFromState(view = state.view) {
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
    if (state.activeFileId) params.set("file", state.activeFileId);
    const file = activeFile();
    if (file && Number.isFinite(selectedIndex(file)))
      params.set("record", String(selectedIndex(file)));
    if (state.activeStore) params.set("store", state.activeStore);
    if (state.storeWork) params.set("work", state.storeWork);
    if (state.storePage > 1) params.set("dbpage", String(state.storePage));
    if (state.storeBrowseMode && state.storeBrowseMode !== "works")
      params.set("browse", state.storeBrowseMode);
    if (view === "pdf" && state.pdf.page > 1) params.set("pdfpage", String(state.pdf.page));
    const tableState = currentTableUrlState(view);
    if (tableState) {
      const compressed = compressUrlState(tableState);
      if (compressed) params.set("ts", compressed);
    }
    let path = viewPathMap[view] || "/";
    // Route-native sub-workspaces can share one compatibility view. Preserve the
    // specific path the router owns so URL synchronization never collapses
    // Source Explorer, Settings sections, or System Data workspaces back to
    // their default sibling.
    if (view === "pdf" && ["/corpus-builder", "/source-explorer"].includes(location.pathname)) {
      path = location.pathname;
    } else if (view === "config" && location.pathname.startsWith("/settings/")) {
      path = location.pathname;
    } else if (
      view === "responsecache" &&
      (location.pathname.startsWith("/system-data/") || location.pathname === "/pipelines")
    ) {
      path = location.pathname;
    }
    const query = params.toString();
    return `${path}${query ? `?${query}` : ""}${url.hash}`;
  }
  function applyUrlState() {
    const params = new URLSearchParams(location.search);
    const pathView = viewFromPath(location.pathname);
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
  return { currentTableUrlState, applyCompressedTableUrlState, urlFromState, applyUrlState };
}
