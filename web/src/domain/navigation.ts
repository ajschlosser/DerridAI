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

import { cloneAuditValue } from "./recordValues";
import { createUrlStateCodec } from "./urlStateCodec";

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
type Deps = { state: Loose; codec?: ReturnType<typeof createUrlStateCodec> } & Record<Helper, Fn>;

export { pathViewMap, viewFromPath, viewPathMap } from "./viewPaths";

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
  const { currentTableUrlState, applyCompressedTableUrlState, urlFromState, applyUrlState } =
    deps.codec || createUrlStateCodec({ state, activeFile, dbSearchWhere, selectedIndex });
  let urlSyncHook: Any = null;
  function getUrlSyncHook() {
    return urlSyncHook;
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
  function setUrlSyncHook(hook: Any) {
    urlSyncHook = typeof hook === "function" ? hook : null;
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
  return {
    getUrlSyncHook,
    navSnapshot,
    setUrlSyncHook,
    currentTableUrlState,
    applyCompressedTableUrlState,
    urlFromState,
    syncUrl,
    applyUrlState,
    navigateTo,
  };
}
