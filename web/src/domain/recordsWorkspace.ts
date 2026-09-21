/* Copyright 2026 Aaron John Schlosser, PhD. */

// The Records workspace: building the rows, columns and selection state the Records view shows, and the commands it
// sends (query, sort, filters, paging, selection, columns, opening a record). Moved verbatim from the legacy runtime;
// the runtime's state object and helpers are passed in as dependencies.
import { sortRows } from "./recordValues";
import { describeRecordsFile } from "./recordsFiles";
import { TABLE_DEFAULTS } from "./runtimeConstants";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "activeFile"
  | "canUse"
  | "clearReviewSelection"
  | "copyCitation"
  | "copyJsonToClipboard"
  | "dbUnavailableReason"
  | "evidenceIsSelected"
  | "getTableColumns"
  | "hasCapability"
  | "hasCorpusDb"
  | "label"
  | "navigateTo"
  | "needsReviewItems"
  | "openBulkFieldEditor"
  | "openOcrCleanupDialog"
  | "openTouchup"
  | "pageInfo"
  | "persistPrefs"
  | "recordDbStatus"
  | "recordStores"
  | "recordsListCell"
  | "refreshPresenceForRows"
  | "reviewKey"
  | "rowMatchesListFilters"
  | "rowsFromReviewSelection"
  | "selectedReviewItems"
  | "setActiveStore"
  | "setListFilterValue"
  | "setReviewSelected"
  | "shell"
  | "syncUrl"
  | "tableAvailableFields"
  | "toast"
  | "toggleSort"
  | "toggleWorkspaceEvidence"
  | "tr"
  | "upsertRows"
  | "urlFromState"
  | "workspaceEvidenceSelectionKey";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createRecordsWorkspace(deps: Deps) {
  const {
    state,
    activeFile,
    canUse,
    clearReviewSelection,
    copyCitation,
    copyJsonToClipboard,
    dbUnavailableReason,
    evidenceIsSelected,
    getTableColumns,
    hasCapability,
    hasCorpusDb,
    label,
    navigateTo,
    needsReviewItems,
    openBulkFieldEditor,
    openOcrCleanupDialog,
    openTouchup,
    pageInfo,
    persistPrefs,
    recordDbStatus,
    recordStores,
    recordsListCell,
    refreshPresenceForRows,
    reviewKey,
    rowMatchesListFilters,
    rowsFromReviewSelection,
    selectedReviewItems,
    setActiveStore,
    setListFilterValue,
    setReviewSelected,
    shell,
    syncUrl,
    tableAvailableFields,
    toast,
    toggleSort,
    toggleWorkspaceEvidence,
    tr,
    upsertRows,
    urlFromState,
    workspaceEvidenceSelectionKey,
  } = deps;
  function clearRecordsListFilters() {
    const f = activeFile();
    if (!f) return;
    state.listFilters[f.id] = {};
    state.pages[f.id] = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function clearRecordsListSelection() {
    clearReviewSelection();
    syncUrl({ replace: true });
  }
  function copyRecordsListCitation(index: Any, kind: Any) {
    const f = activeFile();
    const record = f?.records?.[index];
    if (record) copyCitation(record, kind || "inline");
  }
  function copyRecordsListJson(index: Any) {
    const f = activeFile();
    const record = f?.records?.[index];
    if (record) copyJsonToClipboard(record, record.record_id || "record");
  }
  function getRecordsListShareHref() {
    const path = urlFromState();
    return new URL(path, location.origin).href;
  }
  function getRecordsListSnapshot() {
    const files = state.files.map((file: Any) => describeRecordsFile(file, state.activeFileId));
    const stores = recordStores();
    const shared = Boolean(new URLSearchParams(location.search).get("file"));
    const capabilities = {
      can_select: canUse("editLocalRecords"),
      can_review: canUse("editLocalRecords"),
      can_bulk_edit: canUse("editLocalRecords"),
      can_upsert: canUse("manageCorpus") && hasCorpusDb(),
      can_import: canUse("manageCorpus"),
      can_select_evidence: hasCapability("evidence.select"),
    };
    const f = activeFile();
    if (!f) {
      return {
        available: false,
        shared,
        files,
        file: null,
        query: "",
        rows: [],
        columns: [],
        available_columns: [],
        sort: { key: "page_start", dir: 1 },
        filters: {},
        page: 1,
        pages: 1,
        page_size: state.pageSize,
        start: 0,
        end: 0,
        matched: 0,
        total: 0,
        flagged: 0,
        selection_count: state.reviewSelection.size,
        page_selected: false,
        stores: stores.map((store: Any) => ({ name: store.name, count: Number(store.count || 0) })),
        active_store: state.activeStore || "",
        has_database: stores.length > 0,
        db_unavailable_reason: dbUnavailableReason(),
        capabilities,
      };
    }
    const query = state.searches[f.id] || "";
    const sort = state.sorts[f.id] || (state.sorts[f.id] = { key: "page_start", dir: 1 });
    const filters = state.listFilters[f.id] || {};
    let rows = f.records
      .map((record: Any, index: Any) => ({ file: f, record, index }))
      .filter(
        (x: Any) =>
          !query ||
          String(x.record.text || "")
            .toLocaleLowerCase()
            .includes(query.toLocaleLowerCase()),
      )
      .filter((x: Any) => rowMatchesListFilters(x, filters));
    rows = sortRows(rows, sort);
    const pg = pageInfo(rows.length, state.pages[f.id] || 1);
    state.pages[f.id] = pg.page;
    const slice = rows.slice(pg.start, pg.end);
    try {
      refreshPresenceForRows(slice);
    } catch {
      /* presence is best-effort */
    }
    const flagged = needsReviewItems(
      f.records.map((record: Any, index: Any) => ({ file: f, record, index })),
    ).length;
    const pageSelected =
      slice.length > 0 && slice.every((x: Any) => state.reviewSelection.has(reviewKey(f, x.index)));
    const available = tableAvailableFields(
      f.records.map((record: Any, index: Any) => ({ file: f, record, index })),
      ["__db_status", "work", "page_start", "needs_review", "text"],
    );
    const columnKeys = getTableColumns("list", available);
    return {
      available: true,
      shared,
      files,
      file: describeRecordsFile(f, state.activeFileId),
      query,
      rows: slice.map((x: Any) => {
        const key = reviewKey(f, x.index);
        const evidenceKey = workspaceEvidenceSelectionKey(f, x.index);
        const status = recordDbStatus(f, x.index, x.record);
        return {
          index: x.index,
          key,
          record_id: String(x.record.record_id || `#${x.index + 1}`),
          work: String(x.record.work || ""),
          selected: state.reviewSelection.has(key),
          evidence_selected: evidenceIsSelected(evidenceKey),
          db_status: { kind: status.kind, label: status.label, title: status.title || "" },
          cells: columnKeys.map((column: Any) => recordsListCell(x, column, query)),
        };
      }),
      columns: columnKeys.map((key: Any) => ({ key, label: label(key) })),
      available_columns: available.map((key: Any) => ({ key, label: label(key) })),
      sort: { key: sort.key, dir: sort.dir },
      filters: { ...filters },
      page: pg.page,
      pages: pg.pages,
      page_size: state.pageSize,
      start: pg.start,
      end: pg.end,
      matched: rows.length,
      total: f.records.length,
      flagged,
      selection_count: state.reviewSelection.size,
      page_selected: pageSelected,
      stores: stores.map((store: Any) => ({ name: store.name, count: Number(store.count || 0) })),
      active_store: state.activeStore || "",
      has_database: stores.length > 0,
      db_unavailable_reason: dbUnavailableReason(),
      capabilities,
    };
  }
  function openRecordsListRecord(index: Any) {
    const f = activeFile();
    if (!f) return;
    navigateTo("record", { fileId: f.id, index });
  }
  function recordsListCommand(name: Any) {
    const f = activeFile();
    if (name === "import") {
      (document.querySelector("#fileInput") as HTMLInputElement | null)?.click();
      return Promise.resolve();
    }
    if (name === "ocr")
      return Promise.resolve(
        canUse("editLocalRecords")
          ? openOcrCleanupDialog()
          : toast("Your role does not have permission to edit records."),
      );
    if (!f) return Promise.resolve();
    if (name === "reviewSelected") return Promise.resolve(openTouchup(selectedReviewItems()));
    if (name === "improveSelected")
      return Promise.resolve(openTouchup(selectedReviewItems(), "auto"));
    if (name === "bulkSelected")
      return Promise.resolve(
        openBulkFieldEditor({
          rows: selectedReviewItems(),
          title: tr("search.bulk_edit_selected", "Bulk edit selected records"),
        }),
      );
    if (name === "upsertSelected") return upsertRows(rowsFromReviewSelection(), "selected records");
    if (name === "reviewFlagged")
      return Promise.resolve(
        openTouchup(
          needsReviewItems(
            f.records.map((record: Any, index: Any) => ({ file: f, record, index })),
          ),
        ),
      );
    if (name === "improveFlagged")
      return Promise.resolve(
        openTouchup(
          needsReviewItems(
            f.records.map((record: Any, index: Any) => ({ file: f, record, index })),
          ),
          "auto",
        ),
      );
    if (name === "upsertFile")
      return upsertRows(
        f.records.map((record: Any, index: Any) => ({ file: f, record, index })),
        "records",
      );
    return Promise.resolve();
  }
  function resetRecordsListColumns() {
    state.tableColumns.list = [...TABLE_DEFAULTS.list];
    persistPrefs();
    syncUrl({ replace: true });
  }
  function selectRecordsListMatches() {
    const f = activeFile();
    if (!f) return;
    const query = state.searches[f.id] || "";
    const filters = state.listFilters[f.id] || {};
    const rows = f.records
      .map((record: Any, index: Any) => ({ file: f, record, index }))
      .filter(
        (x: Any) =>
          !query ||
          String(x.record.text || "")
            .toLocaleLowerCase()
            .includes(query.toLocaleLowerCase()),
      )
      .filter((x: Any) => rowMatchesListFilters(x, filters));
    for (const x of rows) state.reviewSelection.add(reviewKey(f, x.index));
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setRecordsListColumns(keys: Any) {
    const list = Array.isArray(keys) ? keys.filter(Boolean) : [];
    if (list.length) state.tableColumns.list = list;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setRecordsListFilter(key: Any, value: Any) {
    const f = activeFile();
    if (!f) return;
    setListFilterValue(f.id, key, value);
    state.pages[f.id] = 1;
    syncUrl({ replace: true });
  }
  function setRecordsListPage(page: Any) {
    const f = activeFile();
    if (!f) return;
    state.pages[f.id] = Math.max(1, Number(page) || 1);
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setRecordsListPageSelected(selected: Any) {
    const snapshot = getRecordsListSnapshot();
    const f = activeFile();
    if (!f) return;
    for (const row of snapshot.rows) setReviewSelected(f, row.index, selected);
    syncUrl({ replace: true });
  }
  function setRecordsListPageSize(size: Any) {
    const f = activeFile();
    if (!f) return;
    state.pageSize = Number(size) || state.pageSize;
    state.pages[f.id] = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setRecordsListQuery(value: Any) {
    const f = activeFile();
    if (!f) return;
    state.searches[f.id] = String(value || "");
    state.pages[f.id] = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setRecordsListRowSelected(index: Any, selected: Any) {
    const f = activeFile();
    if (!f) return;
    setReviewSelected(f, index, selected);
    syncUrl({ replace: true });
  }
  function setRecordsListSort(key: Any) {
    const f = activeFile();
    if (!f) return;
    const sort = state.sorts[f.id] || (state.sorts[f.id] = { key: "page_start", dir: 1 });
    toggleSort(sort, key);
    state.pages[f.id] = 1;
    persistPrefs();
    syncUrl({ replace: true });
  }
  function setRecordsListStore(name: Any) {
    setActiveStore(name);
    shell();
  }
  function toggleRecordsListEvidence(index: Any) {
    const f = activeFile();
    if (!f) return;
    toggleWorkspaceEvidence(f, index);
    shell();
  }
  return {
    clearRecordsListFilters,
    clearRecordsListSelection,
    copyRecordsListCitation,
    copyRecordsListJson,
    getRecordsListShareHref,
    getRecordsListSnapshot,
    openRecordsListRecord,
    recordsListCommand,
    resetRecordsListColumns,
    selectRecordsListMatches,
    setRecordsListColumns,
    setRecordsListFilter,
    setRecordsListPage,
    setRecordsListPageSelected,
    setRecordsListPageSize,
    setRecordsListQuery,
    setRecordsListRowSelected,
    setRecordsListSort,
    setRecordsListStore,
    toggleRecordsListEvidence,
  };
}
