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

import { onBeforeUnmount, ref } from "vue";
import { worksService, type WorksViewPatch } from "../services/works";
import type { WorksSnapshot, WorksViewState } from "../types/works";

/**
 * Vue orchestration for the Works workspace.
 *
 * Runtime compatibility is isolated behind `worksService`; components and this
 * composable depend only on the typed Works command/snapshot contract.
 */
export function useWorksWorkspace() {
  const snapshot = ref<WorksSnapshot | null>(null);
  const viewState = ref<WorksViewState>(worksService.getViewState());
  const error = ref("");

  let request = 0;
  onBeforeUnmount(() => {
    request += 1;
  });

  function load() {
    const next = worksService.getSnapshot();
    if (next) snapshot.value = next;
    viewState.value = worksService.getViewState();
  }

  async function read(operation: typeof worksService.prepare) {
    const current = ++request;
    error.value = "";
    try {
      const result = await operation();
      if (current !== request) return result;
      error.value = String(result?.error || "");
      if (!error.value) load();
      return result;
    } catch (cause) {
      if (current !== request) return;
      error.value = cause instanceof Error ? cause.message : String(cause);
      if (
        cause &&
        typeof cause === "object" &&
        "status" in cause &&
        [401, 403].includes(Number(cause.status))
      )
        snapshot.value = null;
    }
  }
  const prepare = () => read(worksService.prepare);
  const activate = () =>
    read(() => {
      const current = request;
      return worksService.activate(() => {
        if (current !== request) return;
        const next = worksService.getSnapshot();
        // Local corpus hydration is authoritative; optional database/annotation reads can continue.
        // Researcher summaries must await their authorized collection read.
        if (next?.mode === "admin" && next.available) snapshot.value = next;
      });
    });

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
    snapshot.value = null;
    await read(async () => {
      await worksService.setStore(name);
      return worksService.prepare();
    });
  }

  function reset() {
    request += 1;
    snapshot.value = null;
    viewState.value = worksService.getViewState();
    error.value = "";
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
    viewState,
    error,
    reset,
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
