/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { createRuntimeState } from "../../src/runtime/runtimeState";
import { createPinia, setActivePinia } from "pinia";
import { nextTick, watch } from "vue";
import { compareState, searchState, vectorState } from "../../src/state/workspaceState";
import { useCompareStore, useSearchStore, useVectorStore } from "../../src/stores/workspace";

// The values below are what the runtime's own state object held before these fields moved into shared state.
const ORIGINAL_INITIAL_VALUES = {
  stores: [],
  storesLastFetchedAt: 0,
  vectorAutoCreateRequested: false,
  activeStore: "",
  storeSearchResults: [],
  storeSearchLoading: false,
  storeSearchMessage: "",
  storeSearchSort: { key: "similarity", dir: -1 },
  storeRecords: [],
  storeCount: 0,
  storePage: 1,
  storePageSize: 50,
  storeQuery: "",
  storeSearchMode: "",
  storeWork: "",
  storeSort: { key: "", dir: 1 },
  storeFilters: {},
  storeWorks: [],
  storeWorkStats: [],
  storeWorksStore: "",
  storeBrowseMode: "works",
  vectorTab: "overview",
  vectorCollectionFilter: "",
  storePresence: {},
  storePresenceIds: {},
  storePresenceCheckedAt: {},
  compareA: "",
  compareB: "",
  compareMode: "workspace",
  comparePasteA: "",
  comparePasteB: "",
  compareSourceA: "library",
  compareSourceB: "library",
  compareFilter: "changed",
  globalSearch: "",
  globalFilters: [],
  globalSort: { key: "__file", dir: 1 },
  globalPage: 1,
  globalSearchMode: "traditional",
  dbSearchMethod: "similarity",
  dbSearchWhere: {},
  dbSearchFetchK: 100,
  dbSearchLambda: 0.7,
  globalAdvancedOpen: false,
  searchFacetFilters: {},
  searchDatabaseRan: false,
  searchResultLayouts: { traditional: "compact", database: "cards" },
  globalSearchAutoRun: false,
};

describe("per-view workspace state", () => {
  it("still exposes every field on the runtime state with its original initial value", () => {
    const state = createRuntimeState() as unknown as Record<string, unknown>;
    for (const [key, value] of Object.entries(ORIGINAL_INITIAL_VALUES)) {
      expect(state[key], key).toEqual(value);
      expect(Object.keys(state)).toContain(key);
    }
  });

  it("reads and writes through to the shared state and hands back the same objects", () => {
    const state = createRuntimeState();
    const results = [{ id: "a" }];
    state.storeSearchResults = results as never;
    expect(state.storeSearchResults).toBe(results);
    expect(vectorState.storeSearchResults).toBe(results);
    state.storeSearchSort.dir = 1;
    expect(vectorState.storeSearchSort.dir).toBe(1);
    state.compareA = "x";
    expect(compareState.compareA).toBe("x");
    state.globalSearch = "hospitality";
    expect(searchState.globalSearch).toBe("hospitality");
    state.globalSearch = "";
    state.compareA = "";
    state.storeSearchSort.dir = -1;
    state.storeSearchResults = [];
  });

  it("does not leak the version counters onto the runtime state", () => {
    const state = createRuntimeState() as unknown as Record<string, unknown>;
    expect("version" in state).toBe(false);
  });

  it("lets Vue code bind and watch the shared fields through the stores", async () => {
    setActivePinia(createPinia());
    const state = createRuntimeState();
    const vector = useVectorStore();
    const search = useSearchStore();
    const compare = useCompareStore();
    const seen: string[] = [];
    watch(
      () => vector.activeStore,
      (name) => seen.push(name),
    );
    state.activeStore = "derrida_primary";
    await nextTick();
    expect(seen).toEqual(["derrida_primary"]);
    expect(vector.activeStore).toBe("derrida_primary");
    // Writing through the store reaches the runtime, too.
    search.globalSearch = "trace";
    expect(state.globalSearch).toBe("trace");
    compare.compareMode = "paste";
    expect(state.compareMode).toBe("paste");
    state.activeStore = "";
    state.globalSearch = "";
    state.compareMode = "workspace";
  });
});
