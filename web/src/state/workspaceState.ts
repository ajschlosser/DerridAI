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

/** Works workspace: the title filter and the work whose overview is open. */
export function createWorksState() {
  return {
    worksSearch: "",
    workOverview: "",
    worksSort: "title-asc",
    worksNeedsReview: false,
    worksDbStatus: "",
    worksAuthor: "",
    worksView: "cards",
    /** Bumped by the runtime when it re-renders this workspace, so Vue code can watch for in-place changes. */
    version: 0,
  };
}
export const worksState = shallowReactive(createWorksState());

/**
 * The loaded corpus: the JSONL files and the active one. The runtime edits the files and their records in place, so
 * `version` is bumped every time it invalidates its own corpus caches (which it already does after every corpus edit).
 */
export function createCorpusState() {
  return {
    files: [] as Loose[],
    activeFileId: null as string | null,
    /** Bumped whenever the loaded corpus changes, so Vue code can watch for in-place edits. */
    version: 0,
  };
}
export const corpusState = shallowReactive(createCorpusState());

/** Records that the loaded corpus changed. */
export function touchCorpus(): void {
  corpusState.version += 1;
}

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

/** Shell layout preferences: the collapsed sidebar and collection list, the operation dock and collapsed panels. */
export function createLayoutState() {
  return {
    sidebarCollapsed: false,
    collectionsCollapsed: false,
    operationToastsMinimized: false,
    operationStackPosition: null as { left: number; top: number } | null,
    collapsedPanels: {} as Record<string, boolean>,
  };
}
export const layoutState = shallowReactive(createLayoutState());

/** Annotations workspace: the works/records view, its filter, and the annotations fetched from the server. */
export function createAnnotationsState() {
  return {
    annotationView: "works",
    annotationSearch: "",
    serverAnnotations: [] as Loose[],
    serverAnnotationsStore: "",
    annotationsFetchedAt: 0,
  };
}
export const annotationsState = shallowReactive(createAnnotationsState());

/** FAQ view: the search text, the page and which entries are expanded. */
export function createFaqState() {
  return {
    faqSearch: "",
    faqPage: 1,
    faqExpanded: {} as Record<string, boolean>,
  };
}
export const faqState = shallowReactive(createFaqState());

/** Table lists: the selection, search text, filters, page, sort and visible columns, each keyed by list name. */
export function createListState() {
  return {
    selected: {} as Loose,
    searches: {} as Loose,
    listFilters: {} as Loose,
    pages: {} as Loose,
    pageSize: 100,
    sorts: {} as Loose,
    tableColumns: {} as Loose,
  };
}
export const listState = shallowReactive(createListState());

/**
 * Provider and Research configuration: the Research run settings, the application settings and the foreground LLM
 * options. The runtime and Settings replace or edit these objects in place; they are loaded from the server.
 */
export function createConfigState() {
  return {
    ragConfig: {
      // Empty means "resolve the current system Research assignment". Once a
      // run or rerun pins an immutable pipeline version these fields preserve it.
      pipeline_id: "",
      pipeline_version: null,
      source_collection: "",
      locales: ["en", "fr"],
      search_types: ["similarity", "lexical", "mmr"],
      k: 64,
      fetch_k: 500,
      automatic_sizing: false,
      lambda_mult: 0.7,
      rrf_k: 60,
      rerank_top_n: 24,
      reranker: "cross_encoder",
      cross_encoder_model: "cross-encoder/ms-marco-MiniLM-L-6-v2",
      query_decomposition: true,
      query_decomposition_num_predict: 768,
      response_language: "auto",
      evidence_record_char_limit: 12000,
      evidence_total_char_limit: 120000,
      bind_citations: true,
      include_works_cited: true,
      prompt_metadata: {
        evidence: [
          "speaker",
          "quoted_speaker",
          "quoted_author",
          "quoted_work",
          "quoted_position_holder",
          "position_holder",
          "stance",
          "proposition_status",
          "target",
          "discourse_role",
        ],
        context: [],
        record: [],
      },
      auto_grade: false,
      auto_grade_provider_profile_id: "",
      provider_profile_id: "",
      skip_retrieval: false,
      use_prior_response_memory: false,
      use_prior_claim_memory: false,
      memory_profile_id: "",
      prompt: "",
      instructions: "",
      history: [],
      run_history: [],
    },
    appConfig: {
      chat_provider: "ollama",
      chat_model: "gemma4:e2b",
      embedding_provider: "ollama",
      embedding_model: "bge-m3:latest",
      ollama_base_url: "http://host.docker.internal:11434",
      ollama_rag_concurrency: 1,
      openai_base_url: "http://host.docker.internal:3001/v1",
      openai_model: "auto",
      openai_model_mode: "auto",
      openai_model_kind: "any",
      openai_api_key: "",
      default_review_preset: "text",
      default_llm_run_mode: "foreground",
      desktop_notifications: false,
      ui_color_theme: "green",
      ui_color_scheme: "system",
      ui_contrast: "system",
      default_provider_profile: "",
      // Loading a model takes memory and time, and evicts whichever model is in use, so it is not done until asked for.
      warm_default_provider_on_start: false,
      review_provider_profile: "",
      provider_profiles: [],
      background_llm: true,
      openai_num_predict: 4096,
      openai_temperature: 0,
      openai_top_p: 1,
      openai_seed: "",
      openai_extra_options: "{}",
      metadata_num_predict: 768,
      text_num_predict: 4096,
    },
    llmConfig: {
      model: "gemma4:e2b",
      num_ctx: 16384,
      num_predict: "",
      think: "false",
      temperature: 0,
      top_k: 0,
      top_p: 1,
      min_p: "",
      repeat_penalty: 1.1,
      seed: "",
      mirostat: 0,
      mirostat_eta: "",
      mirostat_tau: "",
      keep_alive: "10m",
      extra_options: "{}",
    },
  };
}
export const configState = shallowReactive(createConfigState());

/** The PDF Explorer's open document, page, rotation and search state. Holds non-serialisable objects (the pdf.js document, the File). */
export function createPdfState() {
  return {
    pdf: {
      doc: null,
      file: null,
      url: "",
      name: "",
      title: "",
      author: "",
      page: 1,
      rotation: 0,
      text: "",
      search: "",
      relatedSearch: "",
      extractError: "",
      extractionSource: "",
    },
  };
}
export const pdfState = shallowReactive(createPdfState());

/** Review selection: the record keys ticked for review and the evidence picked per record. */
export function createReviewState() {
  return {
    reviewSelection: new Set<string>(),
    selectedEvidence: {} as Loose,
  };
}
export const reviewState = shallowReactive(createReviewState());
