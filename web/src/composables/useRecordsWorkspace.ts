/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref } from "vue";
import * as runtime from "../runtime/runtime.js";
import type { RecordsCell, RecordsListSnapshot, RecordsRow } from "../types/records";

/**
 * Transitional boundary for the Records workspace.
 *
 * The legacy runtime remains the source of truth for now, but Vue components
 * interact with a small, typed command surface. This keeps the current UI and
 * persisted URL/local-storage behaviour stable while making a later service
 * migration a replacement of this module rather than another view rewrite.
 */
export function useRecordsWorkspace() {
  const snapshot = ref<RecordsListSnapshot | null>(null);

  function load() {
    const next = runtime.getRecordsListSnapshot?.() as RecordsListSnapshot | undefined;
    if (next) snapshot.value = next;
  }
  function activate() {
    runtime.state.view = "list";
    load();
  }
  function setQuery(value: string) {
    runtime.setRecordsListQuery?.(value);
    load();
  }
  function setColumns(keys: string[]) {
    runtime.setRecordsListColumns?.(keys);
    load();
  }
  function resetColumns() {
    runtime.resetRecordsListColumns?.();
    load();
  }
  function openRecord(row: RecordsRow) {
    runtime.openRecordsListRecord?.(row.index);
  }
  function setRowSelected(row: RecordsRow, selected: boolean) {
    runtime.setRecordsListRowSelected?.(row.index, selected);
    load();
  }
  function setPageSelected(selected: boolean) {
    runtime.setRecordsListPageSelected?.(selected);
    load();
  }
  function sort(key: string) {
    runtime.setRecordsListSort?.(key);
    load();
  }
  function setFilter(key: string, value: string) {
    runtime.setRecordsListFilter?.(key, value);
    load();
  }
  function setStore(name: string) {
    runtime.setRecordsListStore?.(name);
    load();
  }
  function setPage(page: number) {
    runtime.setRecordsListPage?.(page);
    load();
  }
  function setPageSize(size: number) {
    runtime.setRecordsListPageSize?.(size);
    load();
  }
  function toggleEvidence(row: RecordsRow) {
    runtime.toggleRecordsListEvidence?.(row.index);
    load();
  }
  function copyCitation(row: RecordsRow, kind: "inline" | "full") {
    runtime.copyRecordsListCitation?.(row.index, kind);
  }
  function searchMetadata(cell: RecordsCell) {
    runtime.recordsListMetadataSearch?.(cell.key, cell.meta_value, cell.meta_contains);
  }
  function selectMatches() {
    runtime.selectRecordsListMatches?.();
    load();
  }
  function clearFilters() {
    runtime.clearRecordsListFilters?.();
    load();
  }
  function clearSelection() {
    runtime.clearRecordsListSelection?.();
    load();
  }
  function shareHref() {
    return runtime.getRecordsListShareHref?.() || location.href;
  }
  function selectFile(id: string) {
    runtime.activateFile?.(id);
    load();
  }
  async function closeFile(id: string) {
    await runtime.closeWorkspaceFile?.(id);
    load();
  }
  async function run(command: string) {
    if (command === "merge") await runtime.triggerMerge?.();
    else if (command === "subset") await runtime.triggerSubset?.();
    else if (command === "export") await runtime.triggerExport?.();
    else await runtime.recordsListCommand?.(command);
    load();
  }

  return {
    snapshot,
    load,
    activate,
    setQuery,
    setColumns,
    resetColumns,
    openRecord,
    setRowSelected,
    setPageSelected,
    sort,
    setFilter,
    setStore,
    setPage,
    setPageSize,
    toggleEvidence,
    copyCitation,
    searchMetadata,
    selectMatches,
    clearFilters,
    clearSelection,
    shareHref,
    selectFile,
    closeFile,
    run,
  };
}
