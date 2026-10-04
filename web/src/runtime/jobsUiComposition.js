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

const { ragGradeEvidencePayload } = sharedRecordPresenters;
const { providerProfiles, providerProfile, providerDisplayName } = providerProfilesService;
createJobsWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  announceOperationDock: (...args) => announceOperationDock(...args),
  api: (...args) => api(...args),
  ensureJobProgressCard: (...args) => ensureJobProgressCard(...args),
  jobLabel: (...args) => jobLabel(...args),
  jobProviderSummary: (...args) => jobProviderSummary(...args),
  navigateTo: (...args) => navigateTo(...args),
  notifyOperationsChanged: (...args) => notifyOperationsChanged(...args),
  persistPrefs: (...args) => persistPrefs(...args),
  recordFingerprint: (...args) => recordFingerprint(...args),
  refreshCorpusBuildsHomeCardOnly: (...args) => refreshCorpusBuildsHomeCardOnly(...args),
  refreshOperationsPanelOnly: (...args) => refreshOperationsPanelOnly(...args),
  refreshRagProgressPanel: (...args) => refreshRagProgressPanel(...args),
  refreshStores: (...args) => refreshStores(...args),
  reviewItemFromKey: (...args) => reviewItemFromKey(...args),
  reviewKey: (...args) => reviewKey(...args),
  shell: (...args) => shell(...args),
  touchupRecordPayload: (...args) => touchupRecordPayload(...args),
  tr: (...args) => tr(...args),
  trf: (...args) => trf(...args),
  updateDbStatusElements: (...args) => updateDbStatusElements(...args),
  updateOperationStackCount: (...args) => updateOperationStackCount(...args),
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
  api: (...args) => api(...args),
  cancelBackgroundJob,
  formatTimestamp: (...args) => formatTimestamp(...args),
  humanDuration: (...args) => humanDuration(...args),
  isResearcher: (...args) => isResearcher(...args),
  jobElapsedSeconds: (...args) => jobElapsedSeconds(...args),
  openJobDetails: (...args) => openJobDetails(...args),
  openJobResults: (...args) => openJobResults(...args),
  openLlmTaskLauncher: (...args) => openLlmTaskLauncher(...args),
  operationViewModel: (...args) => operationViewModel(...args),
  persistPrefs: (...args) => persistPrefs(...args),
  pruneClientJobState,
  ragGradeEvidencePayload: (...args) => ragGradeEvidencePayload(...args),
  ragGradeHtml: (...args) => ragGradeHtml(...args),
  refreshJobs,
  tr: (...args) => tr(...args),
  trf: (...args) => trf(...args),
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
  jobLabel: (...args) => jobLabel(...args),
  jobProgressText: (...args) => jobProgressText(...args),
  jobProviderSummary: (...args) => jobProviderSummary(...args),
  openJobDetails: (...args) => openJobDetails(...args),
  openJobResults: (...args) => openJobResults(...args),
  persistPrefs: (...args) => persistPrefs(...args),
  removeFinishedJob,
  tr: (...args) => tr(...args),
  trf: (...args) => trf(...args),
  uid: (...args) => uid(...args),
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
    api: (...args) => api(...args),
    applyPdfLinkMatch: (...args) => applyPdfLinkMatch(...args),
    applyRecordChanges: (...args) => applyRecordChanges(...args),
    canAccessPage: (...args) => canAccessPage(...args),
    cancelBackgroundJob,
    cloneAuditValue: (...args) => cloneAuditValue(...args),
    formatTimestamp: (...args) => formatTimestamp(...args),
    fullCitation: (...args) => fullCitation(...args),
    isResearcher: (...args) => isResearcher(...args),
    jobLabel: (...args) => jobLabel(...args),
    jsonPretty: (...args) => jsonPretty(...args),
    label: (...args) => label(...args),
    navSnapshot: (...args) => navSnapshot(...args),
    navigateTo: (...args) => navigateTo(...args),
    openWorkMetadataProposalResult: (...args) => openWorkMetadataProposalResult(...args),
    pages: (...args) => pages(...args),
    persistFileNow: (...args) => persistFileNow(...args),
    persistPrefs: (...args) => persistPrefs(...args),
    providerDisplayName: (...args) => providerDisplayName(...args),
    providerProfile: (...args) => providerProfile(...args),
    providerProfiles: (...args) => providerProfiles(...args),
    providerRequestConfig: (...args) => providerRequestConfig(...args),
    pruneClientJobState,
    ragGradeHtml: (...args) => ragGradeHtml(...args),
    recordFingerprint: (...args) => recordFingerprint(...args),
    recordStores: (...args) => recordStores(...args),
    refreshJobs,
    refreshRagProgressPanel: (...args) => refreshRagProgressPanel(...args),
    refreshStores: (...args) => refreshStores(...args),
    renderView: (...args) => renderView(...args),
    reviewDiffSides: (...args) => reviewDiffSides(...args),
    reviewItemFromKey: (...args) => reviewItemFromKey(...args),
    reviewKey: (...args) => reviewKey(...args),
    sanitizeResearchGeneration: (...args) => sanitizeResearchGeneration(...args),
    shell: (...args) => shell(...args),
    shellRefreshHook: refreshShell,
    showAppModal: (...args) => showAppModal(...args),
    startJobPolling,
    syncJobProgressToasts,
    tr: (...args) => tr(...args),
    trf: (...args) => trf(...args),
    uid: (...args) => uid(...args),
    upsertRecordPayload: (...args) => upsertRecordPayload(...args),
    getUrlSyncHook: () => getUrlSyncHook(),
    warmupProviderProfile: (...args) => warmupProviderProfile(...args),
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
  trf: (...args) => trf(...args),
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api: (...args) => api(...args),
  canAccessPage: (...args) => canAccessPage(...args),
  cancelBackgroundJob,
  clearSelectedEvidence: (...args) => clearSelectedEvidence(...args),
  gradeRagResponse: (...args) => gradeRagResponse(...args),
  hasCapability: (...args) => hasCapability(...args),
  hasCorpusDb: (...args) => hasCorpusDb(...args),
  isResearcher: (...args) => isResearcher(...args),
  navigateTo: (...args) => navigateTo(...args),
  persistPrefs: (...args) => persistPrefs(...args),
  providerDisplayName: (...args) => providerDisplayName(...args),
  providerProfile: (...args) => providerProfile(...args),
  providerProfiles: (...args) => providerProfiles(...args),
  pruneClientJobState,
  recordStores: (...args) => recordStores(...args),
  refreshJobs,
  refreshStores: (...args) => refreshStores(...args),
  selectedEvidenceEntries: (...args) => selectedEvidenceEntries(...args),
  selectedEvidencePayload: (...args) => selectedEvidencePayload(...args),
  setEvidence: (...args) => setEvidence(...args),
  shellRefreshHook: refreshShell,
  startJobPolling,
  syncJobProgressToasts,
  tr: (...args) => tr(...args),
  uid: (...args) => uid(...args),
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
