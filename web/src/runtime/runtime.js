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

// Compatibility composition root for workflows that have not yet moved fully into Vue/domain modules.
// Prefer adding new behavior to the focused imports below and expose only the narrow bridge needed here;
// moving logic back into this file makes the remaining runtime migration harder to reason about and test.
import { toast } from "../composables/notifications";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import PdfWorker from "pdfjs-dist/legacy/build/pdf.worker.mjs?worker";
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
import { tr as trCompat, trf as trfCompat } from "./legacyCompat.js";
import { TOUCHUP_GROUPS } from "../domain/runtimeConstants";
import "../domain/runtimeConstants";
import { esc, icon } from "../domain/html";
import { jsonPretty, reviewDiffSides } from "../domain/reviewPresentation";
import { touchupFieldsForRecord } from "../domain/touchupFields";
import "../domain/workMetadata";
import "../domain/numberFormatting";
import { refreshResearcherContentPolicy } from "../domain/researcherInputFilter";
import { wireTabScrollPreservation } from "../domain/tabScrollPreservation";
import "../domain/searchFilterSchema";
import { touchupRecordPayload, upsertRecordPayload } from "../domain/recordPayloads";
import "../domain/recordFormatting";
import { api } from "../domain/legacyApi";
import "../domain/pastedRecord";
import { providerRequestConfig } from "../domain/providerRequest";
import { decorateDisabledControls, showAppModal } from "../domain/disabledControls";
import "../domain/sharedRecordScopes";
import "../domain/recordHistory";
import "../domain/dashboardCharts";
import { workIndex } from "../domain/sharedCorpusAnalytics";
import { updateDbStatusElements, upsertRows } from "../domain/sharedDbPresence";
import { hasCorpusDb, recordStores } from "../domain/storeAvailability";
import { registerOperationHooks } from "../domain/operationHooks";
import { registerOperationProgress } from "../domain/operationProgressHooks";
import "../domain/storeExport";
import { evidenceSelection as sharedEvidenceSelection } from "../domain/sharedSearchSupport";
import { label, normalizeRagGrade, pages } from "../domain/sharedRecordHelpers";
import "../domain/sharedPdfLinking";
import "../domain/sharedRecordWorkspace";
import { recordPresenters as sharedRecordPresenters } from "../domain/sharedRecordPresenters";
import { providerProfilesService, warmupProviderProfile } from "../domain/sharedProviderProfiles";
import "../domain/sharedSearchWorkspace";
import "../domain/tableColumns";
import "../domain/sharedRecordsWorkspace";
import { wireMetadataSearchDelegation } from "../domain/legacyDomListeners";
import "../domain/legacyClickDelegation";
import "../domain/listPaging";
import "../domain/sharedWorksWorkspace";
import { workDialogs } from "../domain/sharedWorkDialogs";
import { operationPresenters } from "../domain/sharedOperationPresenters";
import "../domain/storeWorks";
import { createJobsWorkspace } from "../domain/jobsWorkspace";
import {
  refreshJobs,
  startRealtime,
  startJobPolling,
  pruneClientJobState,
  removeFinishedJob,
  clearFinishedOperations,
  cancelBackgroundJob,
  submitBackgroundLlmJob,
  syncJobProgressToasts,
} from "../domain/jobsActions";
import { registerResearchActions } from "../domain/researchActions";
import { registerVectorStoreActions } from "../domain/vectorStoreActions";
import { registerTouchupActions } from "../domain/touchupActions";
import { registerOperationsPanelHooks } from "../domain/operationsPanelHooks";
import "../domain/sharedDashboardData";
import "../domain/sharedPdfExplorerRenderer";
import { applyPdfLinkMatch, registerPdfLlmTaskHooks } from "../domain/pdfPageLlmActions";
import { createJobDialogs } from "../domain/jobDialogs";
import { normalizeTouchupItems } from "../domain/touchupLauncher";
import "../domain/workDialogs";
import { recordDialogs } from "../domain/sharedRecordDialogs";
import { createOperationDock } from "../domain/operationDock";
import "../domain/clipboardCopy";
import {
  getUrlSyncHook,
  navSnapshot,
  setUrlSyncHook,
  applyUrlState,
  navigateTo,
  renderView,
  repaintAfterLocationChange,
} from "../domain/sharedNavigation";
import "../domain/sharedUrlState";
import "../domain/navigation";
import {
  persistPrefs,
  setShellRefreshHook,
  refreshShell,
  shell,
} from "../domain/sharedWorkspaceStorage";
import * as sharedRecordEditing from "../domain/sharedRecordEditing";
import { createOperationsPanelBridge } from "../domain/operationsPanelBridge";
import "../domain/fileDerivedState";
import "../domain/sharedFileLifecycle";
import { persistFileNow, restoreWorkspace } from "../domain/sharedWorkspacePersistence";
import { checkHealth, warmupConfiguredLlm } from "../domain/sharedAppLifecycle";
import "../domain/sharedCompareLibrary";
import "../domain/recordOptionLabel";
import "../domain/sharedStoreRecords";
import { createResearchWorkspace } from "../domain/researchWorkspace";
import "../domain/sharedAnnotations";
import "../state/jobsState";
import { recordFingerprint } from "../domain/corpusCache";
import { createRuntimeState } from "./runtimeState";
import { createVectorCollectionBridge } from "./vectorCollectionBridge";
import { refreshStores } from "../domain/sharedStores";
import { canAccessPage, canUse, hasCapability, isResearcher } from "../domain/sharedSession";
import "../domain/databaseCreationRequest";
import { applyAppearance } from "../domain/sharedAppearance";
import "../domain/relativeTimeLabel";

pdfjsLib.GlobalWorkerOptions.workerPort = new PdfWorker();

const state = createRuntimeState();

function tr(key, fallback = "") {
  return trCompat(state, key, fallback);
}
function trf(key, fallback, values = {}) {
  return trfCompat(state, key, fallback, values);
}

const { ragGradeEvidencePayload } = sharedRecordPresenters;
const { providerProfiles, providerProfile, defaultProviderProfile, providerDisplayName } =
  providerProfilesService;
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
  clearReviewSelection,
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
function setUserContext(user) {
  const priorId = state.userContext?.id;
  state.userContext = user || null;
  if (priorId !== state.userContext?.id) {
    state.serverAnnotations = [];
    state.serverAnnotationsStore = "";
    state.annotationsFetchedAt = 0;
  }
  if (!canAccessPage(state.view)) state.view = "home";
  void refreshResearcherContentPolicy();
}

const { openUpsertQueue } = recordDialogs;

// Names of the facts shown for an operation (panel rows and the details dialog), translated at render time.

// ---- Operations panel bridge -------------------------------------------------------------
// The panel itself is a Vue component (components/OperationsPanel.vue). The runtime still owns
// job state, the dock, toasts, and the details/results dialogs, so the panel reads a plain view
// model from here and calls back into the existing functions.

// 0.36.10 native Search bridge. SearchView owns presentation while the runtime
// continues to own browser-local corpus state, Chroma transport, evidence
// selection, URL serialization, and the existing LLM review workflows.

/** @param {{field?: string, op?: string, value?: string}} [options] */

function ragGradeHtml(grade = {}) {
  const normalized = normalizeRagGrade(grade);
  const scoreKeys = [
    ["query_relevance", "Query relevance"],
    ["source_binding", "Source binding"],
    ["claim_traceability", "Claim traceability"],
    ["attribution_source_discrimination", "Attribution/source discrimination"],
    ["claim_evidence_fidelity", "Claim/evidence fidelity"],
    ["conceptual_precision", "Conceptual precision"],
    ["coverage", "Coverage"],
    ["interpretive_usefulness", "Interpretive usefulness"],
    ["overall", "Overall"],
  ];
  const sections = [
    ["Strengths", normalized.strengths],
    ["Weaknesses", normalized.weaknesses],
    ["Unsupported or risky claims", normalized.unsupported_or_risky_claims],
  ];
  return `<div class="rag-grade-content"><div class="rag-grade-scores">${scoreKeys.map(([key, name]) => `<div><span>${esc(name)}</span><strong>${esc(normalized.score(key))}</strong><small>/10</small></div>`).join("")}</div><section><b>Summary</b><p>${esc(normalized.summary || "No summary returned.")}</p></section>${sections.map(([name, items]) => `<section><b>${esc(name)}</b><ul>${items.map((item) => `<li>${esc(item)}</li>`).join("") || "<li>None reported.</li>"}</ul></section>`).join("")}</div>`;
}

const vectorCollectionBridge = createVectorCollectionBridge({
  state,
  workIndex,
  recordStores,
  tr,
  trf,
  esc,
  icon,
  api,
  refreshStores,
  persistPrefs,
  upsertRows,
  decorateDisabledControls,
  showAppModal,
});
function notifyVectorStoresChanged() {
  return vectorCollectionBridge.notifyVectorStoresChanged();
}
function openCollectionCreationWizard(options = {}) {
  return vectorCollectionBridge.openCollectionCreationWizard(options);
}

const HIGH_RISK_TOUCHUP_FIELDS = new Set([
  "text",
  "record_id",
  "canonical_work_id",
  "inline_citation",
  "full_citation",
  "edition",
  "year",
  "page_start",
  "page_end",
]);

function touchupWorkspaceInfo(inputItems = null, initialMode = "foreground") {
  const items = normalizeTouchupItems(inputItems);
  const availableFields = [];
  for (const item of items) {
    for (const field of touchupFieldsForRecord(item.record))
      if (!availableFields.includes(field) && field !== "updates") availableFields.push(field);
  }
  const attributionPreset = [
    "speaker",
    "position_holder",
    "target",
    "is_direct_quote",
    "quoted_speaker",
    "quoted_author",
    "quoted_work",
    "quoted_position_holder",
    "quoted_addressee",
    "quoted_referent",
    "quotation_chain",
  ].filter((field) => availableFields.includes(field));
  const semanticPreset = [
    "discourse_role",
    "proposition_status",
    "semantic_function",
    "stance",
    "claim_scope",
    "topics",
    "concepts",
    "persons",
    "works_referenced",
  ].filter((field) => availableFields.includes(field));
  const preset = state.appConfig.default_review_preset;
  return {
    items,
    initialMode,
    availableFields,
    attributionPreset,
    semanticPreset,
    defaultSelection:
      preset === "text" && availableFields.includes("text")
        ? ["text"]
        : preset === "semantic"
          ? semanticPreset
          : attributionPreset,
    groups: TOUCHUP_GROUPS,
    highRiskFields: [...HIGH_RISK_TOUCHUP_FIELDS],
    fieldLabels: Object.fromEntries(availableFields.map((field) => [field, label(field)])),
    profiles: providerProfiles().map((profile) => ({ ...profile, api_key: undefined })),
    providerProfileId:
      state.appConfig.review_provider_profile ||
      state.appConfig.default_provider_profile ||
      defaultProviderProfile()?.id ||
      "",
    defaultMode:
      initialMode === "auto"
        ? "auto"
        : state.appConfig.default_llm_run_mode === "foreground"
          ? "foreground"
          : "background",
  };
}
async function touchupProviderStatus(profileId) {
  const profile = providerProfile(profileId);
  if (!profile)
    return {
      provider: "ollama",
      available: false,
      models: [],
      configured_model: "",
      error: "No provider profile configured",
    };
  try {
    const status = await api("/api/llm/status", {
      method: "POST",
      body: JSON.stringify({
        provider: profile.type,
        base_url: profile.base_url || null,
        api_key: profile.type === "openai" ? profile.api_key || "" : null,
      }),
    });
    state.providerStatuses[profile.id] = status;
    return status;
  } catch (error) {
    return {
      provider: profile.type,
      available: false,
      models: [],
      configured_model: profile.model || "",
      error: error.message,
    };
  }
}
function touchupRequestConfig(profileId, model, fields = []) {
  const profile = providerProfile(profileId);
  const config = providerRequestConfig(profile, { textReview: fields.includes("text") });
  if (config && model) config.model = model;
  return config;
}
async function touchupRequest(item, fields, config, instructions = "") {
  return api("/api/llm/touchup", {
    method: "POST",
    body: JSON.stringify({
      record: touchupRecordPayload(item.file.records[item.index], fields),
      fields,
      instructions,
      model: config.model,
      provider: config.provider,
      base_url: config.base_url,
      api_key: config.api_key,
      ollama: config.ollama,
    }),
  });
}
async function touchupSubmitBackground(items, config, fields, instructions, mode) {
  return submitBackgroundLlmJob(items, config, fields, instructions, mode);
}
function touchupApplyResults(items, results, approvals, all = false, reviewOnly = false) {
  const batchId = uid();
  let appliedFields = 0,
    reviewedRecords = 0;
  for (const item of items) {
    const result = results[item.key];
    if (!result?.proposal) continue;
    const fields = reviewOnly
      ? []
      : all
        ? Object.keys(result.proposal.changes || {})
        : [...(approvals[item.key] || [])];
    const changes = {};
    for (const field of fields)
      if (field in result.proposal.changes) changes[field] = result.proposal.changes[field];
    const record = item.file.records[item.index];
    if (record.needs_review === true) changes.needs_review = false;
    if (
      record.review_reason !== undefined &&
      record.review_reason !== null &&
      record.review_reason !== ""
    )
      changes.review_reason = null;
    appliedFields += applyRecordChanges(item.file, item.index, changes, {
      source: "llm_review",
      model: result.proposal.model,
      batchId,
      rationale: result.proposal.rationale,
    });
    reviewedRecords++;
  }
  clearReviewSelection();
  shell();
  renderView();
  toast(
    trf("runtime.toast.marked_reviewed", {
      records: `${reviewedRecords} ${tr(reviewedRecords === 1 ? "dynamic.record_one" : "dynamic.records")}`,
      fields: `${appliedFields} ${tr(appliedFields === 1 ? "runtime.toast.tracked_field_change_one" : "runtime.toast.tracked_field_change_many")}`,
    }),
    { tone: "success" },
  );
  return { appliedFields, reviewedRecords };
}

function triggerUpsertQueue() {
  return canUse("manageCorpus")
    ? openUpsertQueue()
    : toast(tr("runtime.toast.cannot_manage_dbs"), { tone: "warning" });
}

/**
 * Re-derive runtime view state from the browser location (the router owns the URL) and repaint.
 * Used by browser back/forward and whenever a router navigation settles somewhere the runtime did not expect.
 */
function syncFromLocation() {
  applyUrlState();
  repaintAfterLocationChange();
}

async function bootstrapRuntime() {
  wireTabScrollPreservation();
  wireMetadataSearchDelegation();
  await restoreWorkspace();
  try {
    if (!state.appConfig.ui_color_scheme)
      state.appConfig.ui_color_scheme = localStorage.getItem("derridai.ui.scheme") || "system";
    if (!state.appConfig.ui_contrast)
      state.appConfig.ui_contrast = localStorage.getItem("derridai.ui.contrast") || "system";
  } catch {
    /* localStorage can be blocked */
  }
  applyAppearance({
    ui_color_theme: state.appConfig.ui_color_theme,
    ui_color_scheme: state.appConfig.ui_color_scheme || "system",
    ui_contrast: state.appConfig.ui_contrast || "system",
  });
  try {
    const providerData = await api("/api/system/researcher-providers");
    state.researcherProviderProfiles = Array.isArray(providerData.profiles)
      ? providerData.profiles
      : [];
  } catch (error) {
    console.warn("Could not load researcher provider profiles", error);
    state.researcherProviderProfiles = [];
  }
  if (isResearcher()) {
    state.files = [];
    state.activeFileId = null;
    state.selected = {};
    state.reviewSelection = new Set();
    if (
      ![
        "home",
        "rag",
        "vector",
        "works",
        "global",
        "record",
        "compare",
        "annotations",
        "semanticmap",
        "config",
      ].includes(state.view)
    )
      state.view = "home";
  }
  applyUrlState();
  if (!canAccessPage(state.view)) state.view = "home";
  shell();
  // A native Vue route may be active without #main. In that case bootstrap
  // background health/job state only; the mounted view owns #main and its own render.
  if (document.querySelector("#main")) renderView();
  await checkHealth();
  // One discovery request on startup is not a polling loop. Afterwards job state
  // follows the realtime socket; REST polling runs only as a fallback while the
  // socket is unavailable (docs/REALTIME.md).
  await refreshJobs({ rerender: false });
  startRealtime();
  startJobPolling();
  if (!isResearcher() && state.appConfig.warm_default_provider_on_start === true)
    warmupConfiguredLlm();
}

// 0.31.0 native Research bridge. The Vue Research workspace owns presentation,
// while this compatibility layer continues to own corpus/provider/job state and
// the sparse API contracts introduced in 0.30.11. Keep the bridge intentionally
// operation-specific so native components never need to receive credentials,
// full corpus records, or unrelated runtime state.

// 0.35.10 — Record Player. The Record page is Vue-native; this bridge exposes
// only the current record data and actions needed by that workspace. Audit
// history is summarized separately so the heavyweight `updates` payload never
// becomes ordinary component state.

export { bootstrapRuntime, setShellRefreshHook, setUrlSyncHook, setUserContext, syncFromLocation };
