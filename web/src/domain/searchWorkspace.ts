/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mlaPageSpan } from "./citations";
import { valueMatches } from "./recordQuery";
import { cloneAuditValue, sortRows } from "./recordValues";
import {
  SEARCH_AUTOCOMPLETE_EXCLUDED,
  SEARCH_FILTER_FIELDS,
  SEARCH_LOADED_COLUMNS,
  TABLE_DEFAULTS,
} from "./runtimeConstants";
import { decompressUrlState } from "./urlState";

// The Search workspace: building the results, facets and columns the Search view shows, and the commands it sends
// (scope, query, filters, sort, paging, selection, running a search). Moved verbatim from the legacy runtime; the
// runtime's state object and helpers are passed in as dependencies.

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The runtime's state object and the helpers that still live in the legacy runtime. */
type Helper =
  | "allRows"
  | "api"
  | "applyCompressedTableUrlState"
  | "buildSearchFacets"
  | "canAccessPage"
  | "canUse"
  | "clearReviewSelection"
  | "copyCitation"
  | "dbEvidenceKey"
  | "dbSearchFilterDescriptors"
  | "dbSearchWhere"
  | "evidenceIsSelected"
  | "filterOpsForField"
  | "getTableColumns"
  | "hasCapability"
  | "isResearcher"
  | "label"
  | "navigateTo"
  | "openBulkFieldEditor"
  | "openDatabaseCreationFromResearch"
  | "openStoreRecordEditor"
  | "openTouchup"
  | "persistPrefs"
  | "recordDbStatus"
  | "recordStores"
  | "refreshPresenceForRows"
  | "refreshStores"
  | "reviewItemFromKey"
  | "reviewKey"
  | "searchColumnOptions"
  | "searchFilterDescriptor"
  | "searchMatchReasons"
  | "searchRecordMatchesFacets"
  | "searchRowMatchesFacets"
  | "searchSimilarity"
  | "searchSuggestions"
  | "selectedEvidenceEntries"
  | "selectedReviewItems"
  | "setReviewSelected"
  | "shell"
  | "syncUrl"
  | "tableAvailableFields"
  | "toast"
  | "toggleDbEvidence"
  | "toggleSort"
  | "toggleWorkspaceEvidence"
  | "tr"
  | "uid"
  | "urlFromState"
  | "workspaceEvidenceSelectionKey";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createSearchWorkspace(deps: Deps) {
  const {
    state,
    allRows,
    api,
    applyCompressedTableUrlState,
    buildSearchFacets,
    canAccessPage,
    canUse,
    clearReviewSelection,
    copyCitation,
    dbEvidenceKey,
    dbSearchFilterDescriptors,
    dbSearchWhere,
    evidenceIsSelected,
    filterOpsForField,
    getTableColumns,
    hasCapability,
    isResearcher,
    label,
    navigateTo,
    openBulkFieldEditor,
    openDatabaseCreationFromResearch,
    openStoreRecordEditor,
    openTouchup,
    persistPrefs,
    recordDbStatus,
    recordStores,
    refreshPresenceForRows,
    refreshStores,
    reviewItemFromKey,
    reviewKey,
    searchColumnOptions,
    searchFilterDescriptor,
    searchMatchReasons,
    searchRecordMatchesFacets,
    searchRowMatchesFacets,
    searchSimilarity,
    searchSuggestions,
    selectedEvidenceEntries,
    selectedReviewItems,
    setReviewSelected,
    shell,
    syncUrl,
    tableAvailableFields,
    toast,
    toggleDbEvidence,
    toggleSort,
    toggleWorkspaceEvidence,
    tr,
    uid,
    urlFromState,
    workspaceEvidenceSelectionKey,
  } = deps;
  function localSearchBaseRows() {
    const q = String(state.globalSearch || "")
      .trim()
      .toLocaleLowerCase();
    return allRows().filter(
      (row: Any) =>
        (!q ||
          String(row.record.text || "")
            .toLocaleLowerCase()
            .includes(q)) &&
        state.globalFilters.every((filter: Any) =>
          valueMatches(row.record[filter.field], filter.op, filter.value),
        ),
    );
  }
  function searchScope() {
    return state.globalSearchMode === "database" || isResearcher() ? "database" : "loaded";
  }
  function searchLayout(scope = searchScope()) {
    const key = scope === "database" ? "database" : "traditional";
    const value = state.searchResultLayouts?.[key] || (key === "database" ? "cards" : "compact");
    return ["compact", "roomy", "cards"].includes(value)
      ? value
      : key === "database"
        ? "cards"
        : "compact";
  }
  function searchResultFromKey(key: Any) {
    const token = String(key || "");
    if (token.startsWith("workspace:")) return reviewItemFromKey(token.slice("workspace:".length));
    if (token.startsWith("database:")) {
      const rest = token.slice("database:".length);
      const split = rest.indexOf(":");
      const collection = split >= 0 ? rest.slice(0, split) : state.activeStore;
      const id = split >= 0 ? rest.slice(split + 1) : rest;
      const item = (state.storeSearchResults || []).find(
        (result: Any) =>
          String(result.id || result.record?._chroma_id || result.record?.record_id || "") === id,
      );
      return item ? { collection, id, record: item.record || {}, item } : null;
    }
    return null;
  }
  function buildWorkspaceSearchResult(row: Any) {
    const record = row.record;
    const selectionKey = reviewKey(row.file, row.index);
    const evidenceKey = workspaceEvidenceSelectionKey(row.file, row.index);
    return {
      key: `workspace:${selectionKey}`,
      kind: "workspace",
      file_id: row.file.id,
      file_name: row.file.name,
      index: row.index,
      record_id: String(record.record_id || row.index + 1),
      work: String(record.work || ""),
      page_span: mlaPageSpan(record, { prefix: false }),
      text: String(record.text || ""),
      record: cloneAuditValue(record),
      db_status: recordDbStatus(row.file, row.index, record),
      selected: state.reviewSelection.has(selectionKey),
      evidence_selected: evidenceIsSelected(evidenceKey),
      evidence_available: hasCapability("evidence.select"),
      distance: null,
      similarity: null,
      mmr_score: null,
      match_reasons: searchMatchReasons(record, state.globalSearch, { database: false }),
    };
  }
  function buildDatabaseSearchResult(item: Any) {
    const record = item.record || {};
    const id = String(item.id || record._chroma_id || record.record_id || "");
    const evidenceKey = dbEvidenceKey(state.activeStore, id);
    return {
      key: `database:${state.activeStore}:${id}`,
      kind: "database",
      collection: state.activeStore,
      chroma_id: id,
      record_id: String(record.record_id || id),
      work: String(record.work || ""),
      page_span: mlaPageSpan(record, { prefix: false }),
      text: String(record.text || ""),
      record: cloneAuditValue(record),
      db_status: {
        kind: "exists",
        label: tr("search.db_in_database"),
        title: state.activeStore,
      },
      selected: false,
      evidence_selected: evidenceIsSelected(evidenceKey),
      evidence_available: hasCapability("evidence.select"),
      distance: item.distance ?? null,
      similarity: searchSimilarity(item.distance),
      mmr_score: item.mmr_score ?? null,
      match_reasons: searchMatchReasons(record, state.globalSearch, {
        database: true,
        method: state.dbSearchMethod,
      }),
    };
  }
  function sortDatabaseSearchResults(results: Any) {
    const sort = state.storeSearchSort || { key: "similarity", dir: -1 };
    const dir = Number(sort.dir) || 1;
    const key = sort.key || "similarity";
    return [...results].sort((a, b) => {
      let av, bv;
      if (key === "similarity") {
        av = a.similarity ?? -1;
        bv = b.similarity ?? -1;
      } else if (key === "page_start") {
        av = Number(a.record?.page_start ?? 0);
        bv = Number(b.record?.page_start ?? 0);
      } else {
        av = String(a.record?.[key] ?? "");
        bv = String(b.record?.[key] ?? "");
      }
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return (
        String(av).localeCompare(String(bv), undefined, { numeric: true, sensitivity: "base" }) *
        dir
      );
    });
  }
  async function getSearchWorkspaceSnapshot({ refresh = true, autoRun = true } = {}) {
    // Native Search may be re-entered through Vue breadcrumb/history navigation.
    // Keep the legacy state owner aligned without rewriting the URL that brought
    // the user here; popstate/app bootstrap already restore encoded URL state.
    state.view = "global";
    if (refresh) {
      try {
        await refreshStores();
      } catch (error) {
        console.warn("Search store refresh failed", error);
      }
    }
    const stores = recordStores();
    if (!state.activeStore && stores.length) state.activeStore = stores[0].name;
    if (state.activeStore && !stores.some((store: Any) => store.name === state.activeStore))
      state.activeStore = stores[0]?.name || "";
    if (isResearcher()) state.globalSearchMode = "database";
    if (autoRun && state.globalSearchAutoRun && searchScope() === "database" && stores.length) {
      state.globalSearchAutoRun = false;
      persistPrefs();
      await runSearchWorkspace({ silent: true });
    }
    const scope = searchScope();
    const layout = searchLayout(scope);
    const pageSize = Math.max(10, Number(state.pageSize) || 100);
    let results = [],
      total = 0,
      facets = [],
      suggestions = {},
      available = [],
      filters = [];
    if (scope === "loaded") {
      const base = localSearchBaseRows();
      let rows = base.filter((row: Any) => searchRowMatchesFacets(row));
      rows = sortRows(rows, state.globalSort);
      total = rows.length;
      const pages = Math.max(1, Math.ceil(total / pageSize));
      state.globalPage = Math.max(1, Math.min(pages, Number(state.globalPage) || 1));
      const start = (state.globalPage - 1) * pageSize;
      const slice = rows.slice(start, start + pageSize);
      await refreshPresenceForRows(slice).catch(() => undefined);
      results = slice.map(buildWorkspaceSearchResult);
      facets = buildSearchFacets(base);
      suggestions = searchSuggestions(allRows());
      available = tableAvailableFields(allRows(), ["__file", ...SEARCH_LOADED_COLUMNS]);
      filters = state.globalFilters.map(searchFilterDescriptor);
    } else {
      let dbItems = (state.storeSearchResults || [])
        .map(buildDatabaseSearchResult)
        .filter((result: Any) => searchRecordMatchesFacets(result.record));
      dbItems = sortDatabaseSearchResults(dbItems);
      total = dbItems.length;
      const pages = Math.max(1, Math.ceil(total / pageSize));
      state.globalPage = Math.max(1, Math.min(pages, Number(state.globalPage) || 1));
      const start = (state.globalPage - 1) * pageSize;
      results = dbItems.slice(start, start + pageSize);
      const records = (state.storeSearchResults || []).map((item: Any) => item.record || {});
      facets = buildSearchFacets(records, { database: true });
      suggestions = searchSuggestions(records, { database: true });
      available = tableAvailableFields(
        records.map((record: Any) => ({ record })),
        ["__db_status"],
      );
      filters = dbSearchFilterDescriptors();
    }
    if (!available.includes("__db_status")) available.unshift("__db_status");
    const columns = getTableColumns("global", available);
    const pages = Math.max(1, Math.ceil(total / pageSize));
    const filterFields = [
      ...new Set([
        ...SEARCH_FILTER_FIELDS,
        ...available.filter(
          (field: Any) => !field.startsWith("__") && !SEARCH_AUTOCOMPLETE_EXCLUDED.has(field),
        ),
      ]),
    ]
      .filter(Boolean)
      .sort((a, b) => label(a).localeCompare(label(b)));
    return {
      ready: true,
      is_researcher: isResearcher(),
      scope,
      query: String(state.globalSearch || ""),
      method: ["similarity", "mmr", "filter"].includes(state.dbSearchMethod)
        ? state.dbSearchMethod
        : "similarity",
      fetch_k: Math.max(1, Number(state.dbSearchFetchK) || 100),
      lambda_mult: Math.max(0, Math.min(1, Number(state.dbSearchLambda ?? 0.7))),
      advanced_open: Boolean(state.globalAdvancedOpen),
      stores: stores.map((store: Any) => ({
        name: store.name,
        count: Number(store.count || 0),
        filter_fields: Array.isArray(store.filter_fields) ? store.filter_fields.map(String) : [],
        schema_id: String(store.schema_id || store.metadata?.schema_id || ""),
      })),
      active_store: state.activeStore || "",
      has_database: stores.length > 0,
      has_loaded_records: allRows().length > 0,
      total_loaded_records: allRows().length,
      results,
      total,
      page: state.globalPage,
      page_size: pageSize,
      pages,
      layout,
      sort:
        scope === "database"
          ? state.storeSearchSort || { key: "similarity", dir: -1 }
          : state.globalSort || { key: "__file", dir: 1 },
      columns: searchColumnOptions(columns),
      available_columns: searchColumnOptions(available),
      facets,
      filters,
      filter_fields: searchColumnOptions(filterFields),
      filter_suggestions: suggestions,
      selection_count: state.reviewSelection.size,
      selected_evidence_count: selectedEvidenceEntries().length,
      loading: Boolean(state.storeSearchLoading),
      search_has_run:
        scope === "loaded" || Boolean(state.searchDatabaseRan || state.storeSearchResults.length),
      capabilities: {
        can_select: scope === "loaded" && canUse("editLocalRecords"),
        can_review: scope === "loaded" && canUse("editLocalRecords"),
        can_bulk_edit: scope === "loaded" && canUse("editLocalRecords"),
        can_manage_database: canUse("manageCorpus"),
        can_select_evidence: hasCapability("evidence.select"),
      },
    };
  }
  async function setSearchScope(scope: Any) {
    const next = scope === "database" || isResearcher() ? "database" : "traditional";
    state.globalSearchMode = next;
    state.globalPage = 1;
    state.storeSearchResults = [];
    state.searchDatabaseRan = false;
    persistPrefs();
    syncUrl({ replace: false });
    shell();
    return getSearchWorkspaceSnapshot({ refresh: true, autoRun: false });
  }
  function updateSearchQuery(value: Any, { replace = true } = {}) {
    state.globalSearch = String(value || "");
    state.globalPage = 1;
    persistPrefs();
    syncUrl({ replace });
    return state.globalSearch;
  }
  function setSearchAdvancedOpen(value: Any) {
    state.globalAdvancedOpen = Boolean(value);
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setSearchMethod(method: Any) {
    if (!["similarity", "mmr", "filter"].includes(method)) return;
    if (method !== "filter") {
      const previous = state.dbSearchWhere || {};
      const safe = Object.fromEntries(
        Object.entries(previous).filter(
          ([, value]) =>
            !(
              value &&
              typeof value === "object" &&
              Object.prototype.hasOwnProperty.call(value, "$contains")
            ),
        ),
      );
      if (Object.keys(safe).length !== Object.keys(previous).length) {
        state.dbSearchWhere = safe;
        toast(tr("search.contains_filter_removed"), { tone: "info" });
      }
    }
    state.dbSearchMethod = method;
    state.storeSearchResults = [];
    state.searchDatabaseRan = false;
    state.globalPage = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setSearchStore(name: Any) {
    state.activeStore = recordStores().some((store: Any) => store.name === name)
      ? name
      : recordStores()[0]?.name || "";
    state.storeSearchResults = [];
    state.searchDatabaseRan = false;
    state.globalPage = 1;
    persistPrefs();
    syncUrl({ replace: true });
    shell();
  }
  function setSearchMmrOptions({ fetch_k, lambda_mult }: Loose = {}) {
    if (fetch_k != null) state.dbSearchFetchK = Math.max(1, Math.min(1000, Number(fetch_k) || 100));
    if (lambda_mult != null)
      state.dbSearchLambda = Math.max(0, Math.min(1, Number(lambda_mult) || 0));
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setSearchLayout(layout: Any) {
    if (!["compact", "roomy", "cards"].includes(layout)) return;
    const key = searchScope() === "database" ? "database" : "traditional";
    state.searchResultLayouts = { ...(state.searchResultLayouts || {}), [key]: layout };
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setSearchPage(page: Any) {
    state.globalPage = Math.max(1, Number(page) || 1);
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setSearchPageSize(size: Any) {
    state.pageSize = Math.max(10, Math.min(500, Number(size) || 100));
    state.globalPage = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setSearchColumns(columns: Any) {
    const scope = searchScope();
    const available =
      scope === "loaded"
        ? tableAvailableFields(allRows(), ["__file", ...SEARCH_LOADED_COLUMNS])
        : tableAvailableFields(
            (state.storeSearchResults || []).map((item: Any) => ({ record: item.record || {} })),
            ["__db_status"],
          );
    const requested = [...new Set((columns || []).map(String))].filter((key) =>
      available.includes(key),
    );
    const fallback = scope === "loaded" ? SEARCH_LOADED_COLUMNS : TABLE_DEFAULTS.global;
    state.tableColumns.global = requested.length
      ? requested
      : fallback.filter((key) => available.includes(key));
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setSearchSort(key: Any) {
    if (searchScope() === "database") {
      const sort = state.storeSearchSort || { key: "similarity", dir: -1 };
      state.storeSearchSort = {
        key,
        dir: sort.key === key ? -Number(sort.dir || 1) : key === "similarity" ? -1 : 1,
      };
    } else toggleSort(state.globalSort, key);
    state.globalPage = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function toggleSearchFacet(field: Any, value: Any) {
    const next = { ...(state.searchFacetFilters || {}) };
    const values = new Set(Array.isArray(next[field]) ? next[field].map(String) : []);
    const token = String(value);
    values.has(token) ? values.delete(token) : values.add(token);
    if (values.size) next[field] = [...values];
    else delete next[field];
    state.searchFacetFilters = next;
    state.globalPage = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function clearSearchFacetFilters() {
    state.searchFacetFilters = {};
    state.globalPage = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function clearSearchAllFilters() {
    state.searchFacetFilters = {};
    state.globalFilters = [];
    state.dbSearchWhere = {};
    state.globalPage = 1;
    state.storeSearchResults = [];
    state.searchDatabaseRan = false;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function addSearchAdvancedFilter({ field = "", op = "eq", value = "" } = {}) {
    field = String(field || "");
    value = String(value ?? "").trim();
    if (!field) return;
    if (searchScope() === "database") {
      if (!value) return;
      const next = { ...(state.dbSearchWhere || {}) };
      next[field] = op === "has" ? { $contains: value } : value;
      state.dbSearchWhere = next;
      state.storeSearchResults = [];
      state.searchDatabaseRan = false;
    } else {
      const nextOp = filterOpsForField(field).some(([candidate]: Any) => candidate === op)
        ? op
        : "eq";
      if (!["empty", "notempty"].includes(nextOp) && !value) return;
      state.globalFilters = [
        ...(state.globalFilters || []),
        { id: uid(), field, op: nextOp, value },
      ];
    }
    state.globalPage = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function removeSearchAdvancedFilter(id: Any) {
    if (String(id).startsWith("db:")) {
      const field = String(id).slice(3);
      const next = { ...(state.dbSearchWhere || {}) };
      delete next[field];
      state.dbSearchWhere = next;
      state.storeSearchResults = [];
      state.searchDatabaseRan = false;
    } else
      state.globalFilters = (state.globalFilters || []).filter(
        (filter: Any) => String(filter.id) !== String(id),
      );
    state.globalPage = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  async function runSearchWorkspace({ silent = false } = {}) {
    if (searchScope() !== "database")
      return getSearchWorkspaceSnapshot({ refresh: false, autoRun: false });
    await refreshStores().catch(() => undefined);
    const stores = recordStores();
    if (!stores.length) {
      if (canAccessPage("vector")) openDatabaseCreationFromResearch();
      return getSearchWorkspaceSnapshot({ refresh: false, autoRun: false });
    }
    if (!state.activeStore || !stores.some((store: Any) => store.name === state.activeStore))
      state.activeStore = stores[0].name;
    const method = ["similarity", "mmr", "filter"].includes(state.dbSearchMethod)
      ? state.dbSearchMethod
      : "similarity";
    const query = String(state.globalSearch || "").trim();
    if (method !== "filter" && !query) {
      if (!silent) toast(tr("search.enter_query"), { tone: "warn" });
      return getSearchWorkspaceSnapshot({ refresh: false, autoRun: false });
    }
    state.dbSearchFetchK = Math.max(1, Math.min(1000, Number(state.dbSearchFetchK) || 100));
    state.dbSearchLambda = Math.max(0, Math.min(1, Number(state.dbSearchLambda ?? 0.7)));
    state.storeSearchLoading = true;
    state.searchDatabaseRan = true;
    state.globalPage = 1;
    persistPrefs();
    syncUrl({ replace: true });
    try {
      const safeWhere = safeDbSearchWhere(method);
      state.dbSearchWhere = safeWhere;
      const body = {
        query,
        mode: method,
        n_results: 100,
        where: Object.keys(safeWhere).length ? safeWhere : null,
        fetch_k: state.dbSearchFetchK,
        lambda_mult: state.dbSearchLambda,
      };
      const data = await api(`/api/stores/${encodeURIComponent(state.activeStore)}/search`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      state.storeSearchResults = Array.isArray(data?.results) ? data.results : [];
    } catch (error) {
      state.storeSearchResults = [];
      if (!silent)
        toast(`${tr("research.search_failed")}: ${(error as Error).message}`, {
          tone: "danger",
        });
    } finally {
      state.storeSearchLoading = false;
      persistPrefs();
      syncUrl({ replace: true });
    }
    return getSearchWorkspaceSnapshot({ refresh: false, autoRun: false });
  }
  async function searchResultAction(key: Any, action: Any) {
    const result = searchResultFromKey(key);
    if (!result) return false;
    if (String(key).startsWith("workspace:")) {
      if (action === "open") {
        navigateTo("record", { fileId: result.file.id, index: result.index });
        return true;
      }
      if (action === "citation-inline") {
        await copyCitation(result.record, "inline");
        return true;
      }
      if (action === "citation-full") {
        await copyCitation(result.record, "full");
        return true;
      }
      if (action === "evidence") {
        toggleWorkspaceEvidence(result.file, result.index);
        return true;
      }
      if (action === "select") {
        setReviewSelected(
          result.file,
          result.index,
          !state.reviewSelection.has(reviewKey(result.file, result.index)),
        );
        return true;
      }
    } else {
      if (action === "open" || action === "edit") {
        if (isResearcher()) {
          state.activeStore = result.collection;
          state.researcherRecordId = result.id;
          persistPrefs();
          navigateTo("record");
        } else openStoreRecordEditor({ ...result.record, _chroma_id: result.id });
        return true;
      }
      if (action === "citation-inline") {
        await copyCitation(result.record, "inline");
        return true;
      }
      if (action === "citation-full") {
        await copyCitation(result.record, "full");
        return true;
      }
      if (action === "evidence") {
        toggleDbEvidence(result.collection, result.id, result.record);
        return true;
      }
    }
    return false;
  }
  function setSearchResultSelected(key: Any, selected: Any) {
    const item = searchResultFromKey(key);
    if (item?.file) setReviewSelected(item.file, item.index, Boolean(selected));
  }
  function setSearchPageSelected(keys: Any, selected: Any) {
    for (const key of keys || []) setSearchResultSelected(key, selected);
    persistPrefs();
  }
  function clearSearchSelection() {
    clearReviewSelection();
  }
  function runSearchSelectionAction(action: Any) {
    const items = selectedReviewItems();
    if (!items.length) return;
    if (action === "review") return openTouchup(items);
    if (action === "improve") return openTouchup(items, "auto");
    if (action === "bulk")
      return openBulkFieldEditor({
        rows: items,
        title: tr("search.bulk_edit_selected"),
      });
  }
  function getSearchShareHref() {
    const path = urlFromState();
    return new URL(path, location.origin).href;
  }
  function restoreSearchViewFromHref(href: Any) {
    const url = new URL(String(href || ""), location.origin);
    const token = url.searchParams.get("ts");
    state.view = "global";
    if (token) applyCompressedTableUrlState(decompressUrlState(token), "global");
    const store = url.searchParams.get("store");
    if (store) state.activeStore = store;
    state.storeSearchResults = [];
    state.searchDatabaseRan = false;
    if (searchScope() === "database" && (state.globalSearch || Object.keys(dbSearchWhere()).length))
      state.globalSearchAutoRun = true;
    persistPrefs();
    syncUrl({ replace: false });
    shell();
    return getSearchWorkspaceSnapshot({ refresh: true, autoRun: true });
  }
  function safeDbSearchWhere(method = state.dbSearchMethod) {
    const safe: Loose = {};
    for (const [rawField, rawValue] of Object.entries(dbSearchWhere())) {
      const field = String(rawField || "").trim();
      if (!field || field.startsWith("$")) continue;
      if (
        method === "filter" &&
        rawValue &&
        typeof rawValue === "object" &&
        !Array.isArray(rawValue) &&
        Object.prototype.hasOwnProperty.call(rawValue, "$contains")
      ) {
        const value = String((rawValue as Loose).$contains ?? "").trim();
        if (value) safe[field] = { $contains: value };
        continue;
      }
      if (
        ["string", "number", "boolean"].includes(typeof rawValue) &&
        String(rawValue).trim() !== ""
      )
        safe[field] = rawValue;
    }
    return safe;
  }
  function researcherDbRecords() {
    const map = new Map();
    for (const item of state.storeSearchResults || []) {
      const record = item.record || {};
      const id = String(item.id || record._chroma_id || record.record_id || "");
      if (id) map.set(id, { ...record, _chroma_id: id });
    }
    for (const record of state.storeRecords || []) {
      const id = String(record._chroma_id || record.record_id || "");
      if (id && !map.has(id)) map.set(id, record);
    }
    return [...map.values()];
  }
  return {
    localSearchBaseRows,
    searchScope,
    searchLayout,
    searchResultFromKey,
    buildWorkspaceSearchResult,
    buildDatabaseSearchResult,
    sortDatabaseSearchResults,
    getSearchWorkspaceSnapshot,
    setSearchScope,
    updateSearchQuery,
    setSearchAdvancedOpen,
    setSearchMethod,
    setSearchStore,
    setSearchMmrOptions,
    setSearchLayout,
    setSearchPage,
    setSearchPageSize,
    setSearchColumns,
    setSearchSort,
    toggleSearchFacet,
    clearSearchFacetFilters,
    clearSearchAllFilters,
    addSearchAdvancedFilter,
    removeSearchAdvancedFilter,
    runSearchWorkspace,
    searchResultAction,
    setSearchResultSelected,
    setSearchPageSelected,
    clearSearchSelection,
    runSearchSelectionAction,
    getSearchShareHref,
    restoreSearchViewFromHref,
    safeDbSearchWhere,
    researcherDbRecords,
  };
}
