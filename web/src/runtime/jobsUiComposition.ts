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

// Composition of the jobs workspace, operation dock, operations panel, job dialogs and Research workspace over the
// shared state. These factories depend on each other (the dock and panel open the job dialogs; the dialogs refresh the
// panel), so each helper is wrapped to be looked up when called. Importing this module registers their hooks.
import { tr, trf } from "../domain/sharedTranslate";
import { state } from "../domain/sharedUrlState";
import "diff";
import "../domain/operationsDock";
import "./operationsPanelHost";
import "../domain/operationsPanel";
import { cloneAuditValue } from "../domain/recordValues";
import "../domain/urlState";
import { formatTimestamp } from "../domain/recordTableHelpers";
import "../domain/recordQuery";
import { sanitizeResearchGeneration } from "../domain/researchPayloads";
import { fullCitation } from "../domain/citations";
import "../domain/recordsFiles";
import "../domain/runtimeConstants";
import { jsonPretty, reviewDiffSides } from "../domain/reviewPresentation";
import "../domain/workMetadata";
import "../domain/numberFormatting";
import "../domain/researcherInputFilter";
import "../domain/tabScrollPreservation";
import "../domain/searchFilterSchema";
import { touchupRecordPayload, upsertRecordPayload } from "../domain/recordPayloads";
import "../domain/recordFormatting";
import { api } from "../domain/legacyApi";
import "../domain/pastedRecord";
import { providerRequestConfig } from "../domain/providerRequest";
import { showAppModal } from "../domain/disabledControls";
import "../domain/sharedRecordScopes";
import "../domain/recordHistory";
import "../domain/dashboardCharts";
import { updateDbStatusElements } from "../domain/sharedDbPresence";
import { hasCorpusDb, recordStores } from "../domain/storeAvailability";
import { registerOperationHooks } from "../domain/operationHooks";
import { registerOperationProgress } from "../domain/operationProgressHooks";
import "../domain/storeExport";
import { evidenceSelection as sharedEvidenceSelection } from "../domain/sharedSearchSupport";
import { label, pages } from "../domain/sharedRecordHelpers";
import "../domain/sharedPdfLinking";
import "../domain/sharedRecordWorkspace";
import { recordPresenters as sharedRecordPresenters } from "../domain/sharedRecordPresenters";
import { providerProfilesService, warmupProviderProfile } from "../domain/sharedProviderProfiles";
import "../domain/sharedSearchWorkspace";
import "../domain/tableColumns";
import "../domain/sharedRecordsWorkspace";
import "../domain/legacyDomListeners";
import "../domain/legacyClickDelegation";
import "../domain/listPaging";
import "../domain/sharedWorksWorkspace";
import { workDialogs } from "../domain/sharedWorkDialogs";
import { operationPresenters } from "../domain/sharedOperationPresenters";
import "../domain/storeWorks";
import { createJobsWorkspace } from "../domain/jobsWorkspace";
import {
  refreshJobs,
  startJobPolling,
  pruneClientJobState,
  removeFinishedJob,
  clearFinishedOperations,
  cancelBackgroundJob,
  syncJobProgressToasts,
} from "../domain/jobsActions";
import { registerResearchActions } from "../domain/researchActions";
import {
  notifyVectorStoresChanged,
  openCollectionCreationWizard,
  triggerUpsertQueue,
} from "../domain/sharedVectorCollections";
import { registerVectorStoreActions } from "../domain/vectorStoreActions";
import { registerTouchupActions } from "../domain/touchupActions";
import {
  touchupWorkspaceInfo,
  touchupProviderStatus,
  touchupRequestConfig,
  touchupRequest,
  touchupSubmitBackground,
  touchupApplyResults,
} from "../domain/sharedTouchupWorkflow";
import { registerOperationsPanelHooks } from "../domain/operationsPanelHooks";
import "../domain/sharedDashboardData";
import "../domain/sharedPdfExplorerRenderer";
import { applyPdfLinkMatch, registerPdfLlmTaskHooks } from "../domain/pdfPageLlmActions";
import { ragGradeHtml } from "../domain/ragGradeHtml";
import { createJobDialogs } from "../domain/jobDialogs";
import "../domain/workDialogs";
import { createOperationDock } from "../domain/operationDock";
import "../domain/clipboardCopy";
import { getUrlSyncHook, navSnapshot, navigateTo, renderView } from "../domain/sharedNavigation";
import "../domain/sharedUrlState";
import "../domain/navigation";
import { persistPrefs, refreshShell, shell } from "../domain/sharedWorkspaceStorage";
import * as sharedRecordEditing from "../domain/sharedRecordEditing";
import { createOperationsPanelBridge } from "../domain/operationsPanelBridge";
import "../domain/fileDerivedState";
import "../domain/sharedFileLifecycle";
import { persistFileNow } from "../domain/sharedWorkspacePersistence";
import "../domain/sharedAppLifecycle";
import "../domain/sharedCompareLibrary";
import "../domain/recordOptionLabel";
import "../domain/sharedStoreRecords";
import { createResearchWorkspace } from "../domain/researchWorkspace";
import "../domain/sharedAnnotations";
import "../state/jobsState";
import { recordFingerprint } from "../domain/corpusCache";
import { refreshStores } from "../domain/sharedStores";
import { canAccessPage, hasCapability, isResearcher } from "../domain/sharedSession";
import "../domain/databaseCreationRequest";
import "../domain/sharedAppearance";
import "../domain/relativeTimeLabel";

/* eslint-disable @typescript-eslint/no-explicit-any -- the factories take loosely typed shared helpers */
// Resolves the helper when it is called, not when this module evaluates: several are declared later in this module.
const late =
  (get: () => (...args: any[]) => any) =>
  (...args: any[]) =>
    get()(...args);

const { ragGradeEvidencePayload } = sharedRecordPresenters;
const { providerProfiles, providerProfile, providerDisplayName } = providerProfilesService;
createJobsWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  announceOperationDock: late(() => announceOperationDock),
  api: late(() => api),
  ensureJobProgressCard: late(() => ensureJobProgressCard),
  jobLabel: late(() => jobLabel),
  jobProviderSummary: late(() => jobProviderSummary),
  navigateTo: late(() => navigateTo),
  notifyOperationsChanged: late(() => notifyOperationsChanged),
  persistPrefs: late(() => persistPrefs),
  recordFingerprint: late(() => recordFingerprint),
  refreshCorpusBuildsHomeCardOnly: late(() => refreshCorpusBuildsHomeCardOnly),
  refreshOperationsPanelOnly: late(() => refreshOperationsPanelOnly),
  refreshRagProgressPanel: late(() => refreshRagProgressPanel),
  refreshStores: late(() => refreshStores),
  reviewItemFromKey: late(() => reviewItemFromKey),
  reviewKey: late(() => reviewKey),
  shell: late(() => shell),
  touchupRecordPayload: late(() => touchupRecordPayload),
  tr: late(() => tr),
  trf: late(() => trf),
  updateDbStatusElements: late(() => updateDbStatusElements),
  updateOperationStackCount: late(() => updateOperationStackCount),
});
const {
  notifyOperationsChanged,
  mountOperationsPanelHost,
  refreshOperationsPanelOnly,
  refreshCorpusBuildsHomeCardOnly,
  gradeRagResponse,
  refreshRagProgressPanel,
} = createOperationsPanelBridge({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api: late(() => api),
  cancelBackgroundJob,
  formatTimestamp: late(() => formatTimestamp),
  humanDuration: late(() => humanDuration),
  isResearcher: late(() => isResearcher),
  jobElapsedSeconds: late(() => jobElapsedSeconds),
  openJobDetails: late(() => openJobDetails),
  openJobResults: late(() => openJobResults),
  openLlmTaskLauncher: late(() => openLlmTaskLauncher),
  showAppModal: late(() => showAppModal),
  operationViewModel: late(() => operationViewModel),
  persistPrefs: late(() => persistPrefs),
  pruneClientJobState,
  ragGradeEvidencePayload: late(() => ragGradeEvidencePayload),
  ragGradeHtml: late(() => ragGradeHtml),
  refreshJobs,
  tr: late(() => tr),
  trf: late(() => trf),
});
registerOperationHooks({ refreshOperationsPanelOnly, notifyVectorStoresChanged });
const { applyRecordChanges } = sharedRecordEditing;
const {
  reviewKey,
  reviewItemFromKey,
  selectedEvidenceEntries,
  setEvidence,
  clearSelectedEvidence,
  selectedEvidencePayload,
} = sharedEvidenceSelection;
const {
  announceOperationDock,
  updateOperationStackCount,
  showOperationProgress,
  updateOperationProgress,
  hideOperationProgress,
  ensureJobProgressCard,
} = createOperationDock({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  cancelBackgroundJob,
  clearFinishedOperations,
  jobLabel: late(() => jobLabel),
  jobProgressText: late(() => jobProgressText),
  jobProviderSummary: late(() => jobProviderSummary),
  openJobDetails: late(() => openJobDetails),
  openJobResults: late(() => openJobResults),
  persistPrefs: late(() => persistPrefs),
  removeFinishedJob,
  tr: late(() => tr),
  trf: late(() => trf),
  uid: late(() => uid),
});
registerOperationProgress({
  show: showOperationProgress,
  update: updateOperationProgress,
  hide: hideOperationProgress,
});
const { openJobDetails, openJobResults, openLlmTaskLauncher, openPdfDraftRecord } =
  createJobDialogs({
    state,
    // Wrapped so each helper is looked up when it is called: several are declared later in this module.
    api: late(() => api),
    applyPdfLinkMatch: late(() => applyPdfLinkMatch),
    applyRecordChanges: late(() => applyRecordChanges),
    canAccessPage: late(() => canAccessPage),
    cancelBackgroundJob,
    cloneAuditValue: late(() => cloneAuditValue),
    formatTimestamp: late(() => formatTimestamp),
    fullCitation: late(() => fullCitation),
    isResearcher: late(() => isResearcher),
    jobLabel: late(() => jobLabel),
    jsonPretty: late(() => jsonPretty),
    label: late(() => label),
    navSnapshot: late(() => navSnapshot),
    navigateTo: late(() => navigateTo),
    openWorkMetadataProposalResult: late(() => openWorkMetadataProposalResult),
    pages: late(() => pages),
    persistFileNow: late(() => persistFileNow),
    persistPrefs: late(() => persistPrefs),
    providerDisplayName: late(() => providerDisplayName),
    providerProfile: late(() => providerProfile),
    providerProfiles: late(() => providerProfiles),
    providerRequestConfig: late(() => providerRequestConfig),
    pruneClientJobState,
    ragGradeHtml: late(() => ragGradeHtml),
    recordFingerprint: late(() => recordFingerprint),
    recordStores: late(() => recordStores),
    refreshJobs,
    refreshRagProgressPanel: late(() => refreshRagProgressPanel),
    refreshStores: late(() => refreshStores),
    renderView: late(() => renderView),
    reviewDiffSides: late(() => reviewDiffSides),
    reviewItemFromKey: late(() => reviewItemFromKey),
    reviewKey: late(() => reviewKey),
    sanitizeResearchGeneration: late(() => sanitizeResearchGeneration),
    shell: late(() => shell),
    shellRefreshHook: refreshShell,
    startJobPolling,
    syncJobProgressToasts,
    tr: late(() => tr),
    trf: late(() => trf),
    uid: late(() => uid),
    upsertRecordPayload: late(() => upsertRecordPayload),
    getUrlSyncHook: () => getUrlSyncHook(),
    warmupProviderProfile: late(() => warmupProviderProfile),
  });
registerPdfLlmTaskHooks({ openLlmTaskLauncher, openPdfDraftRecord });
registerOperationsPanelHooks({ mountOperationsPanelHost, openJobResults, gradeRagResponse });
registerVectorStoreActions({ openCollectionCreationWizard, triggerUpsertQueue });
registerTouchupActions({
  touchupWorkspaceInfo,
  touchupProviderStatus,
  touchupRequestConfig,
  touchupRequest,
  touchupSubmitBackground,
  touchupApplyResults,
});
const {
  getResearchWorkspaceSnapshot,
  updateResearchConfig,
  removeResearchEvidence,
  clearResearchEvidence,
  discoverResearchModels,
  refreshResearchJobs,
  cancelResearchJob,
  deleteResearchJob,
  startResearchRun,
  gradeResearchJob,
  prepareResearchRerun,
  prepareRagRerun,
} = createResearchWorkspace({
  state,
  trf: late(() => trf),
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api: late(() => api),
  canAccessPage: late(() => canAccessPage),
  cancelBackgroundJob,
  clearSelectedEvidence: late(() => clearSelectedEvidence),
  gradeRagResponse: late(() => gradeRagResponse),
  hasCapability: late(() => hasCapability),
  hasCorpusDb: late(() => hasCorpusDb),
  isResearcher: late(() => isResearcher),
  navigateTo: late(() => navigateTo),
  persistPrefs: late(() => persistPrefs),
  providerDisplayName: late(() => providerDisplayName),
  providerProfile: late(() => providerProfile),
  providerProfiles: late(() => providerProfiles),
  pruneClientJobState,
  recordStores: late(() => recordStores),
  refreshJobs,
  refreshStores: late(() => refreshStores),
  selectedEvidenceEntries: late(() => selectedEvidenceEntries),
  selectedEvidencePayload: late(() => selectedEvidencePayload),
  setEvidence: late(() => setEvidence),
  shellRefreshHook: refreshShell,
  startJobPolling,
  syncJobProgressToasts,
  tr: late(() => tr),
  uid: late(() => uid),
});
registerOperationsPanelHooks({ prepareRagRerun });
registerResearchActions({
  getResearchWorkspaceSnapshot,
  updateResearchConfig,
  removeResearchEvidence,
  clearResearchEvidence,
  discoverResearchModels,
  refreshResearchJobs,
  cancelResearchJob,
  deleteResearchJob,
  startResearchRun,
  gradeResearchJob,
  prepareResearchRerun,
});
const {
  jobLabel,
  jobProviderSummary,
  jobElapsedSeconds,
  humanDuration,
  jobProgressText,
  operationViewModel,
} = operationPresenters;

const uid = () => crypto.randomUUID();

// Corpus-derived data is read far more often than it changes. Keep one flattened
// index and memoized derived values instead of rebuilding thousands of row
// wrapper objects on every render/chart/filter pass. Any persisted corpus edit
// invalidates the cache synchronously.
const { openWorkMetadataProposalResult } = workDialogs;
