/* Copyright 2026 Aaron John Schlosser, PhD. */

import * as runtime from "../runtime/runtime.js";
import type { WorksDbStatusKind, WorksSnapshot, WorksSort, WorksViewMode } from "../types/works";
import { annotationsService } from "./annotations";
import { requestCorpusFiles } from "./corpusFiles";

export interface WorksViewPatch {
  sort?: WorksSort;
  needsReview?: boolean;
  dbStatus?: WorksDbStatusKind | "";
  author?: string;
  viewMode?: WorksViewMode;
}

export interface WorksPrepareResult {
  error?: string;
}

export interface WorksService {
  getSnapshot(): WorksSnapshot | undefined;
  prepare(): Promise<WorksPrepareResult | undefined>;
  activate(onHydrated?: () => void): Promise<WorksPrepareResult | undefined>;
  setQuery(value: string): void;
  setOverview(work: string): void;
  setView(patch: WorksViewPatch): void;
  setStore(name: string): Promise<void>;
  syncWork(work: string): Promise<void>;
  syncAll(): Promise<void>;
  chooseFiles(): void;
  separateWorks(): void;
  populateAll(): void;
  populateWork(work: string): void;
  editMetadata(work: string): void;
  openAnnotations(work: string): void;
  searchOverview(work: string): void;
  searchRecords(work: string, needsReview?: boolean): void;
  inspectMixed(work: string, field: string): void;
  searchInsight(field: string, value: string): void;
  reviewFlagged(work: string): void;
  autoImprove(work: string): void;
  removeWork(work: string): void;
  browseResearcher(work: string): void;
}

/**
 * Operation-specific compatibility boundary for the Works workspace.
 *
 * The general runtime still owns several corpus and dialog operations, but Vue
 * code no longer imports that facade directly. Each dependency is named here so
 * it can migrate to a typed store/service without changing the composable or UI.
 */
export const worksService: WorksService = {
  getSnapshot: () => runtime.getWorksWorkspaceSnapshot?.() as WorksSnapshot | undefined,

  prepare: () => runtime.prepareWorksWorkspace?.() as Promise<WorksPrepareResult | undefined>,

  async activate(onHydrated) {
    runtime.state.view = "works";
    await runtime.ensureCorpusWorkspaceLoaded?.();
    onHydrated?.();
    return runtime.prepareWorksWorkspace?.() as Promise<WorksPrepareResult | undefined>;
  },

  setQuery: (value) => runtime.setWorksSearch?.(value),
  setOverview: (work) => runtime.setWorksOverview?.(work),
  setView: (patch) => runtime.setWorksView?.(patch),

  async setStore(name) {
    await runtime.setWorksStore?.(name);
  },

  async syncWork(work) {
    await runtime.syncWork?.(work);
  },

  async syncAll() {
    await runtime.syncAllWorks?.();
  },

  chooseFiles: requestCorpusFiles,
  separateWorks: () => runtime.openSeparateWorksModal?.(),
  populateAll: () => runtime.populateAllWorksMetadata?.(),
  populateWork: (work) => runtime.openWorkMetadataLlmDialog?.(work),
  editMetadata: (work) => runtime.openWorkMetadataEditor?.(work),
  openAnnotations: (work) => annotationsService.openWorkAnnotations(work),
  searchOverview: (work) => runtime.searchWorkOverview?.(work),
  searchRecords: (work, needsReview = false) => runtime.searchWorkRecords?.(work, { needsReview }),
  inspectMixed: (work, field) => runtime.inspectWorksMixedField?.(work, field),
  searchInsight: (field, value) => runtime.searchWorksInsight?.(field, value),
  reviewFlagged: (work) => runtime.reviewFlaggedWork?.(work),
  autoImprove: (work) => runtime.autoImproveWork?.(work),
  removeWork: (work) => runtime.removeEntireWork?.(work),
  browseResearcher: (work) => runtime.browseResearcherWork?.(work),
};
