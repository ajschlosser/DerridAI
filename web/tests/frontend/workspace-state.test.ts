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

import { describe, expect, it } from "vitest";
import { createRuntimeState } from "../../src/runtime/runtimeState";
import { createPinia, setActivePinia } from "pinia";
import { nextTick, watch } from "vue";
import {
  compareState,
  corpusState,
  layoutState,
  searchState,
  touchCorpus,
  vectorState,
  worksState,
} from "../../src/state/workspaceState";
import {
  useCompareStore,
  useCorpusStore,
  useAnnotationsStore,
  useFaqStore,
  useConfigStore,
  useLayoutStore,
  useListsStore,
  useSearchStore,
  useVectorStore,
  useWorksStore,
} from "../../src/stores/workspace";

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
  worksSearch: "",
  workOverview: "",
  files: [],
  activeFileId: null,
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

  it("shares the loaded files and the works fields, and reports corpus edits through the version", async () => {
    setActivePinia(createPinia());
    const state = createRuntimeState() as unknown as Record<string, unknown>;
    const corpus = useCorpusStore();
    const works = useWorksStore();
    const files = [{ id: "f1", name: "a.jsonl", records: [] }];
    state.files = files;
    state.activeFileId = "f1";
    expect(corpus.files).toBe(files);
    expect(corpusState.activeFileId).toBe("f1");
    const seen: number[] = [];
    watch(
      () => corpus.version,
      (version) => seen.push(version),
      { flush: "sync" },
    );
    touchCorpus();
    touchCorpus();
    expect(seen).toEqual([corpus.version - 1, corpus.version]);
    state.worksSearch = "Glas";
    state.workOverview = "Glas";
    expect(works.worksSearch).toBe("Glas");
    expect(worksState.workOverview).toBe("Glas");
    state.files = [];
    state.activeFileId = null;
    state.worksSearch = "";
    state.workOverview = "";
  });
});

describe("shell layout state", () => {
  it("keeps the runtime's fields and defaults, and shares them with the layout store", async () => {
    setActivePinia(createPinia());
    const state = createRuntimeState();
    expect(state.sidebarCollapsed).toBe(false);
    expect(state.collectionsCollapsed).toBe(false);
    expect(state.operationToastsMinimized).toBe(false);
    expect(state.operationStackPosition).toBeNull();
    expect(state.collapsedPanels).toEqual({});

    const layout = useLayoutStore();
    const seen: boolean[] = [];
    watch(
      () => layout.sidebarCollapsed,
      (value) => seen.push(value),
    );
    state.sidebarCollapsed = true;
    await nextTick();
    expect(seen).toEqual([true]);
    expect(layoutState.sidebarCollapsed).toBe(true);

    const panels = state.collapsedPanels;
    panels.notes = true;
    expect(layout.collapsedPanels).toBe(panels);
    layoutState.sidebarCollapsed = false;
  });
});

describe("annotations and FAQ state", () => {
  it("keeps the runtime's defaults and shares them with their stores", async () => {
    setActivePinia(createPinia());
    const state = createRuntimeState();
    expect(state.annotationView).toBe("works");
    expect(state.serverAnnotations).toEqual([]);
    expect(state.annotationsFetchedAt).toBe(0);
    expect(state.faqPage).toBe(1);
    expect(state.faqExpanded).toEqual({});

    const faq = useFaqStore();
    const seen: number[] = [];
    watch(
      () => faq.faqPage,
      (value) => seen.push(value),
    );
    state.faqPage = 3;
    await nextTick();
    expect(seen).toEqual([3]);

    const annotations = useAnnotationsStore();
    state.serverAnnotations = [{ id: "a" }];
    expect(annotations.serverAnnotations).toEqual([{ id: "a" }]);
    state.faqPage = 1;
    state.serverAnnotations = [];
  });
});

describe("table list state", () => {
  it("keeps the runtime's defaults and shares them with the lists store", async () => {
    setActivePinia(createPinia());
    const state = createRuntimeState();
    expect(state.pageSize).toBe(100);
    expect(state.selected).toEqual({});
    expect(state.tableColumns).toEqual({});

    const lists = useListsStore();
    const seen: number[] = [];
    watch(
      () => lists.pageSize,
      (value) => seen.push(value),
    );
    state.pageSize = 50;
    await nextTick();
    expect(seen).toEqual([50]);
    const pages = state.pages as Record<string, number>;
    pages.works = 2;
    expect(lists.pages).toBe(pages);
    state.pageSize = 100;
    state.pages = {};
  });
});

describe("configuration, PDF and review state", () => {
  it("keeps the runtime's defaults and shares them with their stores", () => {
    setActivePinia(createPinia());
    const state = createRuntimeState();
    expect(state.ragConfig.k).toBe(64);
    expect(state.appConfig.chat_provider).toBe("ollama");
    expect(state.llmConfig.num_ctx).toBe(16384);
    expect(state.pdf.page).toBe(1);
    expect(state.reviewSelection.size).toBe(0);
    expect(state.selectedEvidence).toEqual({});

    const config = useConfigStore();
    expect(config.ragConfig).toBe(state.ragConfig);
    state.ragConfig = { ...state.ragConfig, k: 8 };
    expect(config.ragConfig.k).toBe(8);
    config.ragConfig = { ...config.ragConfig, k: 64 };
  });
});
