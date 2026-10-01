/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref } from "vue";
import { worksService, type WorksViewPatch } from "../services/works";
import type { WorksSnapshot } from "../types/works";

/**
 * Vue orchestration for the Works workspace.
 *
 * Runtime compatibility is isolated behind `worksService`; components and this
 * composable depend only on the typed Works command/snapshot contract.
 */
export function useWorksWorkspace() {
  const snapshot = ref<WorksSnapshot | null>(null);
  const error = ref("");

  function load() {
    const next = worksService.getSnapshot();
    if (next) snapshot.value = next;
  }

  async function prepare() {
    error.value = "";
    const result = await worksService.prepare();
    error.value = String(result?.error || "");
    load();
    return result;
  }

  async function activate() {
    error.value = "";
    const result = await worksService.activate();
    error.value = String(result?.error || "");
    load();
    return result;
  }

  function setQuery(value: string) {
    worksService.setQuery(value);
    load();
  }

  function setOverview(work: string) {
    worksService.setOverview(work);
    load();
  }

  function setView(patch: WorksViewPatch) {
    worksService.setView(patch);
    load();
  }

  async function setStore(name: string) {
    await worksService.setStore(name);
    await prepare();
  }

  async function syncWork(work: string) {
    await worksService.syncWork(work);
    load();
  }

  async function syncAll() {
    await worksService.syncAll();
    load();
  }

  function chooseJsonl() {
    worksService.chooseFiles();
  }

  function separateWorks() {
    worksService.separateWorks();
  }

  function populateAll() {
    worksService.populateAll();
  }

  function populateWork(work: string) {
    worksService.populateWork(work);
  }

  function editMetadata(work: string) {
    worksService.editMetadata(work);
  }

  function openAnnotations(work: string) {
    worksService.openAnnotations(work);
  }

  function searchOverview(work: string) {
    worksService.searchOverview(work);
  }

  function searchRecords(work: string, needsReview = false) {
    worksService.searchRecords(work, needsReview);
  }

  function inspectMixed(work: string, field: string) {
    worksService.inspectMixed(work, field);
  }

  function searchInsight(field: string, value: string) {
    worksService.searchInsight(field, value);
  }

  function reviewFlagged(work: string) {
    worksService.reviewFlagged(work);
  }

  function autoImprove(work: string) {
    worksService.autoImprove(work);
  }

  function removeWork(work: string) {
    worksService.removeWork(work);
  }

  function browseResearcher(work: string) {
    worksService.browseResearcher(work);
  }

  return {
    snapshot,
    error,
    load,
    prepare,
    activate,
    setQuery,
    setOverview,
    setView,
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
