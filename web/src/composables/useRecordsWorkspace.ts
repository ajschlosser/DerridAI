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

import { getCurrentScope, onScopeDispose, ref, watch } from "vue";
import * as runtime from "../runtime/runtime.js";
import { corpusState } from "../state/workspaceState";
import type { RecordsCell, RecordsListSnapshot, RecordsRow } from "../types/records";
import type { SubsetField, SubsetRequest, SubsetSource } from "../domain/recordSubsets";

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
  const loading = ref(false);
  const error = ref("");
  let disposed = false;
  let activation: Promise<void> | null = null;
  if (getCurrentScope())
    onScopeDispose(() => {
      disposed = true;
    });

  function load() {
    const next = runtime.getRecordsListSnapshot?.() as RecordsListSnapshot | undefined;
    if (next) snapshot.value = next;
  }
  // The loaded corpus also changes outside this view: a file imported or closed, or a record edited elsewhere. Read the
  // snapshot again then, so the rail and table do not keep showing the corpus as it was (a file imported while Records was
  // open used to appear only after leaving and coming back).
  watch(
    () => [corpusState.version, corpusState.activeFileId],
    () => {
      if (snapshot.value) load();
    },
    { flush: "post" },
  );

  function activate(): Promise<void> {
    if (activation) return activation;
    runtime.state.view = "list";
    loading.value = true;
    error.value = "";
    load();
    activation = (async () => {
      try {
        const result = await runtime.ensureCorpusWorkspaceLoaded?.();
        if (disposed) return;
        if (result?.status === "error") throw result.error;
        load();
      } catch (failure) {
        if (!disposed) error.value = failure instanceof Error ? failure.message : String(failure);
      } finally {
        if (!disposed) loading.value = false;
        activation = null;
      }
    })();
    return activation;
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
  function subsetSources(): SubsetSource[] {
    return runtime.subsetSources?.() || [];
  }
  function subsetFields(): SubsetField[] {
    return runtime.subsetFields?.() || [];
  }
  function subsetSourceRecords(source: string): Record<string, unknown>[] {
    return runtime.subsetSourceRecords?.(source) || [];
  }
  function defaultSubsetName(): string {
    return runtime.defaultSubsetName?.() || "subset.jsonl";
  }
  async function createSubset(request: SubsetRequest) {
    const created = await runtime.createSubsetFile(request);
    load();
    return created;
  }
  async function run(command: string) {
    if (command === "merge") await runtime.triggerMerge?.();
    else if (command === "export") await runtime.triggerExport?.();
    else await runtime.recordsListCommand?.(command);
    load();
  }

  return {
    snapshot,
    loading,
    error,
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
    subsetSources,
    subsetFields,
    subsetSourceRecords,
    defaultSubsetName,
    createSubset,
  };
}
