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

import { ensureCorpusWorkspaceLoaded } from "../domain/sharedCorpusHydration";
import { workDialogs } from "../domain/sharedWorkDialogs";
import { worksWorkspace } from "../domain/sharedWorksWorkspace";
import { state } from "../domain/sharedUrlState";
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
 * Every dependency is a shared module; Vue code does not import the legacy runtime. Each is named here so
 * it can migrate to a typed store/service without changing the composable or UI.
 */
export const worksService: WorksService = {
  getSnapshot: () => worksWorkspace.getWorksWorkspaceSnapshot() as WorksSnapshot | undefined,

  prepare: () => worksWorkspace.prepareWorksWorkspace() as Promise<WorksPrepareResult | undefined>,

  async activate(onHydrated) {
    state.view = "works";
    await ensureCorpusWorkspaceLoaded();
    onHydrated?.();
    return worksWorkspace.prepareWorksWorkspace() as Promise<WorksPrepareResult | undefined>;
  },

  setQuery: (value) => worksWorkspace.setWorksSearch(value),
  setOverview: (work) => worksWorkspace.setWorksOverview(work),
  setView: (patch) => worksWorkspace.setWorksView(patch),

  async setStore(name) {
    await worksWorkspace.setWorksStore(name);
  },

  async syncWork(work) {
    await worksWorkspace.syncWork(work);
  },

  async syncAll() {
    await worksWorkspace.syncAllWorks();
  },

  chooseFiles: requestCorpusFiles,
  separateWorks: () => workDialogs.openSeparateWorksModal(),
  populateAll: () => worksWorkspace.populateAllWorksMetadata(),
  populateWork: (work) => worksWorkspace.openWorkMetadataLlmDialogForVue(work),
  editMetadata: (work) => worksWorkspace.openWorkMetadataEditorForVue(work),
  openAnnotations: (work) => annotationsService.openWorkAnnotations(work),
  searchOverview: (work) => worksWorkspace.searchWorkOverview(work),
  searchRecords: (work, needsReview = false) =>
    worksWorkspace.searchWorkRecords(work, { needsReview }),
  inspectMixed: (work, field) => worksWorkspace.inspectWorksMixedField(work, field),
  searchInsight: (field, value) => worksWorkspace.searchWorksInsight(field, value),
  reviewFlagged: (work) => worksWorkspace.reviewFlaggedWork(work),
  autoImprove: (work) => worksWorkspace.autoImproveWork(work),
  removeWork: (work) => worksWorkspace.removeEntireWork(work),
  browseResearcher: (work) => worksWorkspace.browseResearcherWork(work),
};
