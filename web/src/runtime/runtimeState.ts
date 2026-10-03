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

import { bindJobsState } from "../state/jobsState";
import {
  annotationsState,
  bindSharedState,
  compareState,
  corpusState,
  faqState,
  configState,
  layoutState,
  listState,
  pdfState,
  reviewState,
  searchState,
  vectorState,
  worksState,
} from "../state/workspaceState";

// Initial value of the legacy runtime's single mutable workspace state. Moved verbatim from
// runtime.js so the shape has one home; the runtime still owns the instance it creates.

export function createRuntimeState() {
  const state = {
    userContext: null,
    view: "home",
    researcherRecordId: "",
    researcherCompareA: "",
    researcherCompareB: "",
    dashboardMetricIndex: 0,
    lastViewedRecord: null,
    foregroundUpsertCancelRequested: false,
    recordFind: "",
    recordFindKey: "",
    health: null,
    llmStatus: null,
    researcherProviderProfiles: [],
    translations: { locale: "en-US", dictionary: {}, base: {} },
    providerStatuses: {},
    providerWarmups: {},
    upsertState: {},
    upsertIgnored: {},
    operationProgress: {},
    jobsPollTimer: null,
    foregroundUpsertActive: false,
    warmup: { status: "idle", message: "" },
    storageReady: false,
  };
  // Background-job and per-view workspace fields live in stores shared with Vue code; see state/jobsState.ts and
  // state/workspaceState.ts.
  const withJobs = bindJobsState(state);
  const withVector = bindSharedState(withJobs, vectorState);
  const withCompare = bindSharedState(withVector, compareState);
  const withSearch = bindSharedState(withCompare, searchState);
  const withWorks = bindSharedState(withSearch, worksState);
  const withCorpus = bindSharedState(withWorks, corpusState);
  const withLayout = bindSharedState(withCorpus, layoutState);
  const withAnnotations = bindSharedState(withLayout, annotationsState);
  const withFaq = bindSharedState(withAnnotations, faqState);
  const withLists = bindSharedState(withFaq, listState);
  const withConfig = bindSharedState(withLists, configState);
  const withPdf = bindSharedState(withConfig, pdfState);
  return bindSharedState(withPdf, reviewState);
}

export type RuntimeState = ReturnType<typeof createRuntimeState>;
