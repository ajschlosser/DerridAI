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

import { toRefs } from "vue";
import { defineStore } from "pinia";
import {
  annotationsState,
  compareState,
  configState,
  corpusState,
  faqState,
  layoutState,
  listState,
  pdfState,
  reviewState,
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

/** Shell layout preferences (collapsed sidebar, operation dock position, collapsed panels); persisted by the runtime. */
export const useLayoutStore = defineStore("layout", () => ({ ...toRefs(layoutState) }));

/** Annotations workspace: view, filter and the annotations fetched from the server. */
export const useAnnotationsStore = defineStore("annotations", () => ({
  ...toRefs(annotationsState),
}));

/** FAQ view: search text, page and expanded entries; persisted by the runtime. */
export const useFaqStore = defineStore("faq", () => ({ ...toRefs(faqState) }));

/** Table lists: selection, search, filters, paging, sort and columns per list; persisted by the runtime. */
export const useListsStore = defineStore("lists", () => ({ ...toRefs(listState) }));

/** Research, application and LLM configuration as loaded from the server. */
export const useConfigStore = defineStore("config", () => ({ ...toRefs(configState) }));

/** PDF Explorer document and viewing state. */
export const usePdfStore = defineStore("pdf", () => ({ ...toRefs(pdfState) }));

/** Review selection and chosen evidence. */
export const useReviewStore = defineStore("review", () => ({ ...toRefs(reviewState) }));
