/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReactive } from "vue";

// Workspace state that used to live only on the legacy runtime's `state` object, one shallow-reactive group per view.
// The runtime reads and writes it through accessors on its own `state` (see bindSharedState), so its code is unchanged
// and it still receives the same plain arrays and objects it always did; Vue code reads it through the stores in
// `stores/`. Assigning a field is visible to Vue; in-place edits of arrays and objects are not (the runtime does
// those), so a view that needs them should also watch the group's `version`, which the runtime bumps where it re-renders.

type Loose = Record<string, unknown>;

/** Vector Stores workspace: collections, the active collection, search and browse state, and presence checks. */
export function createVectorState() {
  return {
    stores: [] as Loose[],
    storesLastFetchedAt: 0,
    vectorAutoCreateRequested: false,
    activeStore: "",
    storeSearchResults: [] as Loose[],
    storeSearchLoading: false,
    storeSearchMessage: "",
    storeSearchSort: { key: "similarity", dir: -1 },
    storeRecords: [] as Loose[],
    storeCount: 0,
    storePage: 1,
    storePageSize: 50,
    storeQuery: "",
    storeSearchMode: "",
    storeWork: "",
    storeSort: { key: "", dir: 1 },
    storeFilters: {} as Loose,
    storeWorks: [] as Loose[],
    storeWorkStats: [] as Loose[],
    storeWorksStore: "",
    storeBrowseMode: "works",
    vectorTab: "overview",
    vectorCollectionFilter: "",
    storePresence: {} as Loose,
    storePresenceIds: {} as Loose,
    storePresenceCheckedAt: {} as Loose,
    /** Bumped by the runtime when it re-renders this workspace, so Vue code can watch for in-place changes. */
    version: 0,
  };
}
export const vectorState = shallowReactive(createVectorState());

/** Compare workspace: the two records being compared and how they are chosen. */
export function createCompareState() {
  return {
    compareA: "",
    compareB: "",
    compareMode: "workspace",
    comparePasteA: "",
    comparePasteB: "",
    compareSourceA: "library",
    compareSourceB: "library",
    compareFilter: "changed",
    /** Bumped by the runtime when it re-renders this workspace, so Vue code can watch for in-place changes. */
    version: 0,
  };
}
export const compareState = shallowReactive(createCompareState());

/** Search workspace: the query, filters, sort, paging and database-search options. */
export function createSearchState() {
  return {
    globalSearch: "",
    globalFilters: [] as Loose[],
    globalSort: { key: "__file", dir: 1 },
    globalPage: 1,
    globalSearchMode: "traditional",
    dbSearchMethod: "similarity",
    dbSearchWhere: {} as Loose,
    dbSearchFetchK: 100,
    dbSearchLambda: 0.7,
    globalAdvancedOpen: false,
    searchFacetFilters: {} as Loose,
    searchDatabaseRan: false,
    searchResultLayouts: { traditional: "compact", database: "cards" },
    globalSearchAutoRun: false,
    /** Bumped by the runtime when it re-renders this workspace, so Vue code can watch for in-place changes. */
    version: 0,
  };
}
export const searchState = shallowReactive(createSearchState());

/** Makes each field of `shared` read and write the shared state through `target`, enumerable like the plain field it replaces. */
export function bindSharedState<T extends object, S extends object>(
  target: T,
  shared: S,
  skip: readonly string[] = ["version"],
): T & Omit<S, "version"> {
  for (const key of Object.keys(shared)) {
    if (skip.includes(key)) continue;
    Object.defineProperty(target, key, {
      enumerable: true,
      configurable: true,
      get: () => (shared as Record<string, unknown>)[key],
      set: (value) => {
        (shared as Record<string, unknown>)[key] = value;
      },
    });
  }
  return target as T & Omit<S, "version">;
}
