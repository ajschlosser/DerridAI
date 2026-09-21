/* Copyright 2026 Aaron John Schlosser, PhD. */
import { toRefs } from "vue";
import { defineStore } from "pinia";
import {
  compareState,
  corpusState,
  searchState,
  vectorState,
  worksState,
} from "../state/workspaceState";

// Views of the per-view workspace state that the legacy runtime still owns. Each field is a ref onto the same shared
// object the runtime reads and writes, so Vue code can bind to it and watch it. Assignments are reactive; in-place
// edits of arrays and objects (which the runtime makes) are not, so watch `version` as well when you need those.

/** Vector Stores workspace: collections, the active collection, search and browse state. */
export const useVectorStore = defineStore("vector", () => ({ ...toRefs(vectorState) }));

/** Compare workspace: the two records being compared and how they are chosen. */
export const useCompareStore = defineStore("compare", () => ({ ...toRefs(compareState) }));

/** Search workspace: the query, filters, sort, paging and database-search options. */
export const useSearchStore = defineStore("search", () => ({ ...toRefs(searchState) }));

/** Works workspace: the title filter and the work whose overview is open. */
export const useWorksStore = defineStore("works", () => ({ ...toRefs(worksState) }));

/** The loaded JSONL files and the active one. Watch `version` for edits the runtime makes in place. */
export const useCorpusStore = defineStore("corpus", () => ({ ...toRefs(corpusState) }));
