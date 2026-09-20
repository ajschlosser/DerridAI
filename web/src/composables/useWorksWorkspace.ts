/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref } from "vue";
import * as runtime from "../runtime/runtime.js";
import type { WorksSnapshot } from "../types/works";

type WorksRuntime = typeof runtime & Record<string, ((...args: unknown[]) => unknown) | undefined>;
const worksRuntime = runtime as WorksRuntime;

/**
 * Transitional boundary for the Works workspace.
 *
 * The legacy runtime remains the source of truth for loaded JSONL records,
 * corpus-database sync, and bibliographic dialogs. Vue reads a typed snapshot
 * and issues operation-specific commands so a later service migration can
 * replace this module without rewriting the page.
 */
export function useWorksWorkspace() {
  const snapshot = ref<WorksSnapshot | null>(null);
  const error = ref("");

  function load() {
    const next = runtime.getWorksWorkspaceSnapshot?.() as WorksSnapshot | undefined;
    if (next) snapshot.value = next;
  }

  async function prepare() {
    error.value = "";
    const result = (await runtime.prepareWorksWorkspace?.()) as {error?: string} | undefined;
    error.value = String(result?.error || "");
    load();
    return result;
  }

  async function activate() {
    runtime.state.view = "works";
    await prepare();
  }

  function setQuery(value: string) {
    runtime.setWorksSearch?.(value);
    load();
  }

  function setOverview(work: string) {
    runtime.setWorksOverview?.(work);
    load();
  }

  async function setStore(name: string) {
    await runtime.setWorksStore?.(name);
    await prepare();
  }

  async function syncWork(work: string) {
    await runtime.syncWork?.(work);
    load();
  }

  async function syncAll() {
    await runtime.syncAllWorks?.();
    load();
  }

  function chooseJsonl() {
    document.querySelector<HTMLInputElement>("#fileInput")?.click();
  }

  function separateWorks() {
    runtime.openSeparateWorksModal?.();
  }

  function populateAll() {
    worksRuntime.populateAllWorksMetadata?.();
  }

  function populateWork(work: string) {
    runtime.openWorkMetadataLlmDialog?.(work);
  }

  function editMetadata(work: string) {
    runtime.openWorkMetadataEditor?.(work);
  }

  function openAnnotations(work: string) {
    runtime.openWorkAnnotations?.(work);
  }

  function searchOverview(work: string) {
    runtime.searchWorkOverview?.(work);
  }

  function searchRecords(work: string, needsReview = false) {
    runtime.searchWorkRecords?.(work, {needsReview});
  }

  function inspectMixed(work: string, field: string) {
    worksRuntime.inspectWorksMixedField?.(work, field);
  }

  function searchInsight(field: string, value: string) {
    worksRuntime.searchWorksInsight?.(field, value);
  }

  function reviewFlagged(work: string) {
    worksRuntime.reviewFlaggedWork?.(work);
  }

  function autoImprove(work: string) {
    worksRuntime.autoImproveWork?.(work);
  }

  function removeWork(work: string) {
    worksRuntime.removeEntireWork?.(work);
  }

  function browseResearcher(work: string) {
    worksRuntime.browseResearcherWork?.(work);
  }

  return {
    snapshot,
    error,
    load,
    prepare,
    activate,
    setQuery,
    setOverview,
    setStore,
    syncWork,
    syncAll,
    chooseJsonl,
    separateWorks,
    populateAll,
    populateWork,
    editMetadata,
    openAnnotations,
    searchOverview,
    searchRecords,
    inspectMixed,
    searchInsight,
    reviewFlagged,
    autoImprove,
    removeWork,
    browseResearcher,
  };
}
