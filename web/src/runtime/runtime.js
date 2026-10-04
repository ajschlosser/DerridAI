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
import { openMessageDialog } from "../composables/messageDialog";
import { toast } from "../composables/notifications";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import PdfWorker from "pdfjs-dist/legacy/build/pdf.worker.mjs?worker";
import { diffWordsWithSpace } from "diff";
import {
  dockCollapsedSummary,
  isActiveJobStatus,
  isTerminalJobStatus,
  jobIdsToPruneFromDock,
  jobProgressPercent,
  shouldMountOperationDock,
  statusBadgeTone,
} from "../domain/operationsDock";
import { mountOperationsPanel, unmountOperationsPanel } from "./operationsPanelHost";
import { formatDuration } from "../domain/operationsPanel";
import { cloneAuditValue, compareValues, sameValue, sortRows } from "../domain/recordValues";
import { compressUrlState, decompressUrlState } from "../domain/urlState";
import { formatTimestamp, localRecordKey, toggleSort } from "../domain/recordTableHelpers";
import {
  countOccurrences,
  flattenValueList,
  parseJsonl,
  valueMatches,
} from "../domain/recordQuery";
import {
  finiteResearchNumber,
  normalizedResearchConfig,
  researchEvidenceForUi,
  researchJobForUi,
  researchProfileForUi,
  sanitizeResearchGeneration,
} from "../domain/researchPayloads";
import {
  fullCitation,
  inlineCitation,
  mlaAuthorName,
  mlaPageSpan,
  mlaSentence,
} from "../domain/citations";
import { describeRecordsFile, serializableRecordsFile } from "../domain/recordsFiles";
import {
  applyUiTheme as applyUiThemeCompat,
  setTranslationDictionary as setTranslationDictionaryCompat,
  syncColorScheme as syncColorSchemeCompat,
  tr as trCompat,
  trf as trfCompat,
  translateDynamicUiValue as translateDynamicUiValueCompat,
  translateLegacyDom as translateLegacyDomCompat,
} from "./legacyCompat.js";
import {
  TOUCHUP_CREATABLE_FIELDS,
  TOUCHUP_GROUPS,
  WORK_METADATA_LLM_FIELDS,
} from "../domain/runtimeConstants";
import {
  FIELD_LABELS,
  SEARCH_AUTOCOMPLETE_EXCLUDED,
  SEARCH_FACET_FIELDS,
  SEARCH_FILTER_FIELDS,
  SEARCH_LOADED_COLUMNS,
  viewConfig,
} from "../domain/runtimeConstants";
import { esc, icon } from "../domain/html";
import {
  annotationMatches,
  jsonPretty,
  llmDiffSides,
  ragAnswerHtml,
  reviewDiffSides,
} from "../domain/reviewPresentation";
import { touchupFieldsForRecord } from "../domain/touchupFields";
import {
  commonWorkValue,
  parseProposedMetadataValue,
  representativeWorkMetadata,
  workCoverUrl,
  workOverviewMetadataRows,
} from "../domain/workMetadata";
import { compactNumber } from "../domain/numberFormatting";
import { normalizeResearcherToken } from "../domain/researcherContentFilter";
import { filterOpsForField } from "../domain/searchFilterSchema";
import { stripLigaturesAndArtifacts } from "../domain/textCleanup";
import {
  compactRecordHistory,
  isResponseCacheStore,
  normalizePdfLinkChanges,
  pdfLinks,
  ragEvidenceRecordPayload,
  recordPayload,
  touchupRecordPayload,
  upsertRecordPayload,
} from "../domain/recordPayloads";
import {
  highlight,
  highlightTerms,
  modelOptionLabel,
  openAiModelMatchesKind,
  semanticSimilarity,
  snippet,
} from "../domain/recordFormatting";
import { api } from "../domain/legacyApi";
import { parsePastedRecord } from "../domain/pastedRecord";
import { providerRequestConfig } from "../domain/providerRequest";
import { decorateDisabledControls, showAppModal } from "../domain/disabledControls";
import {
  activeFile,
  bulkEditRowsForScope,
  cleanRows,
  download,
  downloadBlob,
  fileJsonl,
  needsReviewItems,
  selectedRecord,
} from "../domain/sharedRecordScopes";
import { recordHistoryVersions, upsertAuditDelta } from "../domain/recordHistory";
import { barChart, lineChart, multiLineChart, pieChart, statList } from "../domain/dashboardCharts";
import { createOperationPresenters } from "../domain/operationPresenters";
import {
  workIndex,
  dateKeys,
  topNeedsReviewWorkSeries,
  needsReviewTimeline,
  topFieldValues,
  publicationYearSeries,
  workRecordShares,
  averageRecordLengthForTopWorks,
  recentAuditChanges,
} from "../domain/sharedCorpusAnalytics";
import {
  recordDbStatus,
  workDbStatus,
  refreshPresenceForRows,
  updateDbStatusElements,
  ignoredFingerprint,
  pendingUpsertRows,
  pendingChangesForRow,
  removeFromUpsertQueue,
  buildUpsertItems,
  upsertRows,
  rowsFromReviewSelection,
} from "../domain/sharedDbPresence";
import {
  candidateChromaIds,
  corpusStoreExists,
  dbUnavailableReason,
  hasChromaService,
  hasCorpusDb,
  recordStores,
  storeReceipt,
} from "../domain/storeAvailability";
import { registerOperationHooks } from "../domain/operationHooks";
import { registerOperationProgress } from "../domain/operationProgressHooks";
import { exportStoreJsonl } from "../domain/storeExport";
import {
  searchFacets as sharedSearchFacets,
  evidenceSelection as sharedEvidenceSelection,
} from "../domain/sharedSearchSupport";
import {
  label,
  display,
  normalizeRagGrade,
  parseBulkFieldValue,
  parseWorkMetadataValue,
  pages,
  recordFields,
  dbSearchWhere,
} from "../domain/sharedRecordHelpers";
import { recordPresenters as sharedRecordPresenters } from "../domain/sharedRecordPresenters";
import { providerProfilesService, warmupProviderProfile } from "../domain/sharedProviderProfiles";
import { searchWorkspace } from "../domain/sharedSearchWorkspace";
import { getTableColumns, tableAvailableFields } from "../domain/tableColumns";
import { recordsWorkspace as sharedRecordsWorkspace } from "../domain/sharedRecordsWorkspace";
import { activateFile, searchByMetadata } from "../domain/workspaceActions";
import { pageInfo, setActiveStore, setListFilterValue } from "../domain/listPaging";
import { createRecordWorkspace } from "../domain/recordWorkspace";
import { createWorksWorkspace } from "../domain/worksWorkspace";
import { createJobsWorkspace } from "../domain/jobsWorkspace";
import {
  refreshJobs,
  startRealtime,
  startJobPolling,
  pruneClientJobState,
  removeFinishedJob,
  clearFinishedOperations,
  syncUpsertJobReceipts,
  cancelBackgroundJob,
  submitBackgroundLlmJob,
  registerExternalJob,
  maybeDesktopNotify,
  syncJobProgressToasts,
} from "../domain/jobsActions";
import { createDashboardRenderer } from "../domain/dashboardRenderer";
import { createPdfExplorerRenderer } from "../domain/pdfExplorerRenderer";
import { createJobDialogs } from "../domain/jobDialogs";
import { normalizeTouchupItems, openTouchup } from "../domain/touchupLauncher";
import { createWorkDialogs } from "../domain/workDialogs";
import { recordDialogs } from "../domain/sharedRecordDialogs";
import { createOperationDock } from "../domain/operationDock";
import { copyCitation, copyJsonToClipboard } from "../domain/clipboardCopy";
import {
  getUrlSyncHook,
  navSnapshot,
  setUrlSyncHook,
  currentTableUrlState,
  applyCompressedTableUrlState,
  urlFromState,
  syncUrl,
  applyUrlState,
  navigateTo,
  renderView,
} from "../domain/sharedNavigation";
import { selectedIndex, sharedUrlStateCodec } from "../domain/sharedUrlState";
import { pathViewMap, viewFromPath, viewPathMap } from "../domain/navigation";
import {
  workspaceDb,
  workspacePrefs,
  persistPrefs,
  flushWorkspacePrefs,
  setShellRefreshHook,
  refreshShell,
  shell,
} from "../domain/sharedWorkspaceStorage";
import * as sharedRecordEditing from "../domain/sharedRecordEditing";
import { createOperationsPanelBridge } from "../domain/operationsPanelBridge";
import { createPdfLinking } from "../domain/pdfLinking";
import { clearFileDerivedState as clearFileDerivedStateOf } from "../domain/fileDerivedState";
import { closeFile, importFiles } from "../domain/sharedFileLifecycle";
import {
  fileTimers,
  persistFile,
  persistFileNow,
  restoreWorkspace,
} from "../domain/sharedWorkspacePersistence";
import { createAppLifecycle } from "../domain/appLifecycle";
import { compareSearchIndex, lookupRecord } from "../domain/sharedCompareLibrary";
import { recordOptionLabel } from "../domain/recordOptionLabel";
import { loadStorePage, researcherDbRecords } from "../domain/sharedStoreRecords";
import { createResearchWorkspace } from "../domain/researchWorkspace";
import { annotationsWorkspace } from "../domain/sharedAnnotations";
import { subscribeToJobChanges, touchJobs } from "../state/jobsState";
import {
  allRows,
  corpusCache,
  invalidateCorpusCache,
  memoCorpus,
  recordFingerprint,
} from "../domain/corpusCache";
import { createRuntimeState } from "./runtimeState";
import { createVectorCollectionBridge } from "./vectorCollectionBridge";
import { refreshStores } from "../domain/sharedStores";
import { canAccessPage, canUse, hasCapability, isResearcher } from "../domain/sharedSession";
import { openDatabaseCreationFromResearch } from "../domain/databaseCreationRequest";
import { applyAppearance } from "../domain/sharedAppearance";
import { relativeTimeLabel } from "../domain/relativeTimeLabel";

pdfjsLib.GlobalWorkerOptions.workerPort = new PdfWorker();

const state = createRuntimeState();

function syncColorScheme() {
  return syncColorSchemeCompat(state);
}
function applyUiTheme(theme) {
  return applyUiThemeCompat(state, theme);
}

function setTranslationDictionary(locale, dictionary = {}, base = {}, info = {}) {
  return setTranslationDictionaryCompat(state, locale, dictionary, base, info);
}
function tr(key, fallback = "") {
  return trCompat(state, key, fallback);
}
function trf(key, fallback, values = {}) {
  return trfCompat(state, key, fallback, values);
}
function translateDynamicUiValue(value) {
  return translateDynamicUiValueCompat(state, value);
}
function translateLegacyDom(root = document.querySelector("#main")) {
  return translateLegacyDomCompat(state, root);
}

const {
  searchFacetRawValues,
  searchFacetDisplay,
  searchFacetMatches,
  searchRowMatchesFacets,
  searchRecordMatchesFacets,
  searchFacetCountsFromRows,
  searchFacetCountsFromRecords,
  buildSearchFacets,
  searchSuggestions,
  searchFilterDescriptor,
  dbSearchFilterDescriptors,
  searchColumnOptions,
  searchSimilarity,
  searchMatchReasons,
  rowMatchesListFilters,
} = sharedSearchFacets;
const {
  uniqueWorkValues,
  normalizedRecordAnnotation,
  workInsightPieHtml,
  flattenedMetricValues,
  topRecordFieldShare,
  topRecordFieldValues,
  workInsightMetrics,
  mixedWorkValueButton,
  workMetadataControlSpec,
  dashboardPieChart,
  pieShareSeries,
  dashboardMetricBody,
  worksBiblioValue,
  emptyWorksBiblio,
  describeResearcherWork,
  pager,
  ragEvidencePreview,
  storeCellHtml,
  recordsListCell,
  metadataSearchable,
  searchRecordOptions,
  ragGradeEvidencePayload,
} = sharedRecordPresenters;
const {
  ensureProviderProfiles,
  providerProfiles,
  providerProfile,
  defaultProviderProfile,
  providerDisplayName,
  refreshProviderStatuses,
  getProviderProfilesForUi,
  getProviderRequestConfigForUi,
  saveProviderProfilesForUi,
  addProviderProfileForUi,
  removeProviderProfileForUi,
  setDefaultProviderProfileForUi,
  testProviderProfileForUi,
  warmProviderProfileForUi,
  getWarmOnStartForUi,
  setWarmOnStartForUi,
  getDefaultProviderProfileId,
  getProviderStatusesForUi,
  getProviderWarmupsForUi,
} = providerProfilesService;
const {
  localSearchBaseRows,
  searchScope,
  searchLayout,
  searchResultFromKey,
  buildWorkspaceSearchResult,
  buildDatabaseSearchResult,
  sortDatabaseSearchResults,
  getSearchWorkspaceSnapshot,
  setSearchScope,
  updateSearchQuery,
  setSearchAdvancedOpen,
  setSearchMethod,
  setSearchStore,
  setSearchMmrOptions,
  setSearchLayout,
  setSearchPage,
  setSearchPageSize,
  setSearchColumns,
  setSearchSort,
  toggleSearchFacet,
  clearSearchFacetFilters,
  clearSearchAllFilters,
  addSearchAdvancedFilter,
  removeSearchAdvancedFilter,
  runSearchWorkspace,
  searchResultAction,
  setSearchResultSelected,
  setSearchPageSelected,
  clearSearchSelection,
  runSearchSelectionAction,
  getSearchShareHref,
  restoreSearchViewFromHref,
  safeDbSearchWhere,
} = searchWorkspace;
const {
  clearRecordsListFilters,
  clearRecordsListSelection,
  copyRecordsListCitation,
  copyRecordsListJson,
  getRecordsListShareHref,
  getRecordsListSnapshot,
  openRecordsListRecord,
  recordsListCommand,
  resetRecordsListColumns,
  selectRecordsListMatches,
  setRecordsListColumns,
  setRecordsListFilter,
  setRecordsListPage,
  setRecordsListPageSelected,
  setRecordsListPageSize,
  setRecordsListQuery,
  setRecordsListRowSelected,
  setRecordsListSort,
  setRecordsListStore,
  toggleRecordsListEvidence,
} = sharedRecordsWorkspace;
const {
  recordWorkspaceRecord,
  researcherCurrentRecord,
  getRecordWorkspaceSnapshot,
  getRecordObjectGraph,
  getDerridaiNormativeModel,
  recordWorkspaceNavigate,
  setRecordWorkspaceFind,
  toggleCurrentRecordEvidence,
  toggleCurrentRecordReviewSelection,
  copyCurrentRecordCitation,
  copyCurrentRecordJson,
  saveCurrentRecordChanges,
  addCurrentRecordAnnotation,
  replyToCurrentAnnotation,
  removeCurrentRecordAnnotation,
  currentRecordPrimaryAction,
  searchCurrentRecordMetadata,
  navigateRecordWorkspace,
} = createRecordWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  activeFile: (...args) => activeFile(...args),
  api: (...args) => api(...args),
  applyRecordChanges: (...args) => applyRecordChanges(...args),
  canAccessPage: (...args) => canAccessPage(...args),
  canUse: (...args) => canUse(...args),
  cleanRecord: (...args) => cleanRecord(...args),
  copyJsonToClipboard: (...args) => copyJsonToClipboard(...args),
  dbEvidenceKey: (...args) => dbEvidenceKey(...args),
  evidenceIsSelected: (...args) => evidenceIsSelected(...args),
  hasCapability: (...args) => hasCapability(...args),
  hasCorpusDb: (...args) => hasCorpusDb(...args),
  isResearcher: (...args) => isResearcher(...args),
  linkPdfPage: (...args) => linkPdfPage(...args),
  loadStorePage: (...args) => loadStorePage(...args),
  loadedPdfPagesForRecord: (...args) => loadedPdfPagesForRecord(...args),
  navigateTo: (...args) => navigateTo(...args),
  normalizedRecordAnnotation: (...args) => normalizedRecordAnnotation(...args),
  openLoadedPdfPage: (...args) => openLoadedPdfPage(...args),
  openPdfExplorerWorkspace: (...args) => openPdfExplorerWorkspace(...args),
  openRecordHistoryBrowser: (...args) => openRecordHistoryBrowser(...args),
  openTouchup,
  pdfDisplayTitle: (...args) => pdfDisplayTitle(...args),
  persistPrefs: (...args) => persistPrefs(...args),
  refreshServerAnnotations: (...args) => refreshServerAnnotations(...args),
  refreshStores: (...args) => refreshStores(...args),
  researcherDbRecords: (...args) => researcherDbRecords(...args),
  reviewKey: (...args) => reviewKey(...args),
  searchByMetadata: (...args) => searchByMetadata(...args),
  selectedIndex: (...args) => selectedIndex(...args),
  selectedRecord: (...args) => selectedRecord(...args),
  setReviewSelected: (...args) => setReviewSelected(...args),
  shell: (...args) => shell(...args),
  syncUrl: (...args) => syncUrl(...args),
  toggleDbEvidence: (...args) => toggleDbEvidence(...args),
  toggleWorkspaceEvidence: (...args) => toggleWorkspaceEvidence(...args),
  tr: (...args) => tr(...args),
  uid: (...args) => uid(...args),
  unlinkAllPdfLinks: (...args) => unlinkAllPdfLinks(...args),
  unlinkPdfLink: (...args) => unlinkPdfLink(...args),
  upsertRows: (...args) => upsertRows(...args),
  workspaceEvidenceKey: (...args) => workspaceEvidenceKey(...args),
});
const {
  describeAdminWork,
  worksSnapshotBase,
  prepareWorksWorkspace,
  getWorksWorkspaceSnapshot,
  setWorksSearch,
  setWorksOverview,
  setWorksView,
  setWorksStore,
  syncWork,
  syncAllWorks,
  searchWorkRecords,
  searchWorkOverview,
  openWorkMetadataEditorForVue,
  openWorkMetadataLlmDialogForVue,
  openWorkAnnotations,
  populateAllWorksMetadata,
  inspectWorksMixedField,
  searchWorksInsight,
  reviewFlaggedWork,
  autoImproveWork,
  removeEntireWork,
  browseResearcherWork,
} = createWorksWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allAnnotations: (...args) => allAnnotations(...args),
  canUse: (...args) => canUse(...args),
  dbUnavailableReason: (...args) => dbUnavailableReason(...args),
  describeResearcherWork: (...args) => describeResearcherWork(...args),
  display: (...args) => display(...args),
  hasCorpusDb: (...args) => hasCorpusDb(...args),
  isResearcher: (...args) => isResearcher(...args),
  label: (...args) => label(...args),
  navigateTo: (...args) => navigateTo(...args),
  needsReviewItems: (...args) => needsReviewItems(...args),
  openMixedWorkValuesDialog: (...args) => openMixedWorkValuesDialog(...args),
  openRemoveWorkModal: (...args) => openRemoveWorkModal(...args),
  openTouchup,
  openWorkMetadataEditor: (...args) => openWorkMetadataEditor(...args),
  openWorkMetadataLlmDialog: (...args) => openWorkMetadataLlmDialog(...args),
  persistPrefs: (...args) => persistPrefs(...args),
  providerProfiles: (...args) => providerProfiles(...args),
  recordStores: (...args) => recordStores(...args),
  refreshPresenceForRows: (...args) => refreshPresenceForRows(...args),
  refreshServerAnnotations: (...args) => refreshServerAnnotations(...args),
  refreshStoreWorks: (...args) => refreshStoreWorks(...args),
  refreshStores: (...args) => refreshStores(...args),
  searchByMetadata: (...args) => searchByMetadata(...args),
  setActiveStore: (...args) => setActiveStore(...args),
  syncUrl: (...args) => syncUrl(...args),
  tr: (...args) => tr(...args),
  uid: (...args) => uid(...args),
  uniqueWorkValues: (...args) => uniqueWorkValues(...args),
  upsertRows: (...args) => upsertRows(...args),
  workDbStatus: (...args) => workDbStatus(...args),
  workIndex: (...args) => workIndex(...args),
  workInsightMetrics: (...args) => workInsightMetrics(...args),
  worksBiblioValue: (...args) => worksBiblioValue(...args),
});
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
  openSharedAnnotationRecord,
  dashboardTotals,
  dashboardWorkspaceRecordTarget,
  dashboardRecordPreview,
} = createDashboardRenderer({
  state,
  openAnnotationsWorkspaceRecord: (...args) => openAnnotationsWorkspaceRecord(...args),
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allRows: (...args) => allRows(...args),
  api: (...args) => api(...args),
  applyUiTheme: (...args) => applyUiTheme(...args),
  canAccessPage: (...args) => canAccessPage(...args),
  compactNumber: (...args) => compactNumber(...args),
  dashboardMetricBody: (...args) => dashboardMetricBody(...args),
  dbSearchWhere: (...args) => dbSearchWhere(...args),
  decorateDisabledControls: (...args) => decorateDisabledControls(...args),
  defaultProviderProfile: (...args) => defaultProviderProfile(...args),
  formatTimestamp: (...args) => formatTimestamp(...args),
  hasCapability: (...args) => hasCapability(...args),
  isResearcher: (...args) => isResearcher(...args),
  label: (...args) => label(...args),
  memoCorpus: (...args) => memoCorpus(...args),
  mountOperationsPanelHost: (...args) => mountOperationsPanelHost(...args),
  navigateTo: (...args) => navigateTo(...args),
  openDatabaseCreationFromResearch,
  persistPrefs: (...args) => persistPrefs(...args),
  pieShareSeries: (...args) => pieShareSeries(...args),
  providerDisplayName: (...args) => providerDisplayName(...args),
  recentAnnotations: (...args) => recentAnnotations(...args),
  recentAuditChanges: (...args) => recentAuditChanges(...args),
  recordStores: (...args) => recordStores(...args),
  refreshServerAnnotations: (...args) => refreshServerAnnotations(...args),
  refreshStoreWorks: (...args) => refreshStoreWorks(...args),
  refreshStores: (...args) => refreshStores(...args),
  relativeTime: (...args) => relativeTime(...args),
  renderCorpusBuildsHomeCard: (...args) => renderCorpusBuildsHomeCard(...args),
  renderOperationsPanel: (...args) => renderOperationsPanel(...args),
  researcherDbRecords: (...args) => researcherDbRecords(...args),
  responseCacheStore: (...args) => responseCacheStore(...args),
  searchByMetadata: (...args) => searchByMetadata(...args),
  syncUrl: (...args) => syncUrl(...args),
  tr: (...args) => tr(...args),
  trf: (...args) => trf(...args),
  uid: (...args) => uid(...args),
  wireCorpusBuildsHomeCard: (...args) => wireCorpusBuildsHomeCard(...args),
  workIndex: (...args) => workIndex(...args),
  workInsightMetrics: (...args) => workInsightMetrics(...args),
});
const { warmupConfiguredLlm, checkHealth } = createAppLifecycle({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api: (...args) => api(...args),
  defaultProviderProfile: (...args) => defaultProviderProfile(...args),
  ensureProviderProfiles: (...args) => ensureProviderProfiles(...args),
  isResearcher: (...args) => isResearcher(...args),
  persistPrefs: (...args) => persistPrefs(...args),
  warmupProviderProfile,
  refreshProviderStatuses: (...args) => refreshProviderStatuses(...args),
  refreshStoreWorks: (...args) => refreshStoreWorks(...args),
  refreshStores: (...args) => refreshStores(...args),
  renderView: (...args) => renderView(...args),
  shell: (...args) => shell(...args),
  updateSystemCard: (...args) => updateSystemCard(...args),
});
const {
  pdfDisplayTitle,
  loadedPdfPagesForRecord,
  allLinkedRowsForLoadedPdf,
  openPdfExplorerWorkspace,
  openLoadedPdfPage,
  linkedPdfRows,
  linkPdfPage,
  unlinkPdfLink,
  unlinkAllPdfLinks,
} = createPdfLinking({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allRows: (...args) => allRows(...args),
  applyRecordChanges: (...args) => applyRecordChanges(...args),
  normalizePdfLinkChanges: (...args) => normalizePdfLinkChanges(...args),
  pdfLinks: (...args) => pdfLinks(...args),
  renderView: (...args) => renderView(...args),
  shell: (...args) => shell(...args),
  tr: (...args) => tr(...args),
  trf: (...args) => trf(...args),
});
const {
  notifyOperationsChanged,
  operationsBridge,
  renderOperationsPanel,
  mountOperationsPanelHost,
  refreshOperationsPanelOnly,
  wireCorpusBuildsHomeCard,
  refreshCorpusBuildsHomeCardOnly,
  gradeRagResponse,
  removeRagJob,
  clearFinishedRagJobs,
  ragProgressPanelHtml,
  wireRagProgressPanel,
  refreshRagProgressPanel,
  renderCorpusBuildsHomeCard,
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
const {
  applyRecordChanges,
  clearRecordUpdates,
  clearAllUpdates,
  historyVersionChanges,
  restoreRecordHistoryVersion,
} = sharedRecordEditing;
const {
  reviewKey,
  reviewItemFromKey,
  selectedReviewItems,
  workspaceEvidenceKey,
  dbEvidenceKey,
  selectedEvidenceEntries,
  evidenceIsSelected,
  setEvidence,
  workspaceDbEvidenceTarget,
  workspaceEvidenceSelectionKey,
  toggleWorkspaceEvidence,
  toggleDbEvidence,
  clearSelectedEvidence,
  selectedEvidencePayload,
  setReviewSelected,
  clearReviewSelection,
} = sharedEvidenceSelection;
const {
  applyOperationStackPosition,
  setOperationDockMinimized,
  announceOperationDock,
  operationDockCardStats,
  wireOperationStackDrag,
  progressStack,
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
const {
  openJobDetails,
  openJobResults,
  openRagResult,
  openReviewRecordPreview,
  openLlmToolResult,
  openLlmTaskLauncher,
  openPdfDraftRecord,
} = createJobDialogs({
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
const {
  renderPdfCanvas,
  extractPdfPageBrowser,
  extractPdfApi,
  extractPdfPageSmart,
  extractPdfAllSmart,
} = createPdfExplorerRenderer({
  state,
  tr: (...args) => tr(...args),
  trf: (...args) => trf(...args),
});
const {
  researchConfigForUi,
  getResearchWorkspaceSnapshot,
  updateResearchConfig,
  removeResearchEvidence,
  clearResearchEvidence,
  discoverResearchModels,
  refreshResearchJobs,
  getResearchJob,
  cancelResearchJob,
  deleteResearchJob,
  generationFromProfile,
  startResearchRun,
  gradeResearchJob,
  prepareResearchRerun,
  getResponseFaqPage,
  gradeResponseFaqRecord,
  rerunResponseFaqRecord,
  rememberRagPrompt,
  rememberRagRun,
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
const {
  serverAnnotationItems,
  refreshServerAnnotations,
  allAnnotations,
  recentAnnotations,
  annotationTimeline,
  getAnnotationsWorkspaceSnapshot,
  annotationWorkspaceItem,
  loadAnnotationsWorkspace,
  setAnnotationsWorkspaceQuery,
  setAnnotationsWorkspaceView,
  openAnnotationsWorkspaceRecord,
  openAnnotationsWorkspaceWork,
  removeAnnotationsWorkspaceItem,
} = annotationsWorkspace;
const {
  jobLabel,
  jobProviderSummary,
  jobElapsedSeconds,
  humanDuration,
  fact,
  decisionLabel,
  operationIcon,
  operationResultKind,
  operationSubtitle,
  jobProgressText,
  operationDetailPairs,
  operationViewModel,
} = createOperationPresenters({
  tr,
  trf,
  getLocale: () => state.translations?.locale || "en-US",
  getStores: () => state.stores,
  providerProfiles: () => providerProfiles(),
  providerDisplayName: (profile) => providerDisplayName(profile),
});

function systemCardHtml() {
  const health = state.health;
  if (!health) {
    return `<div class="system-row"><span>API</span><span class="system-value"><i class="status-dot warn"></i>Checking</span></div>
      <div class="system-row"><span>Chroma</span><span class="system-value"><i class="status-dot"></i>Unknown</span></div>
      <div class="system-row"><span>Ollama</span><span class="system-value"><i class="status-dot"></i>Unknown</span></div>`;
  }
  const apiOk = health?.ok === true;
  const chromaOk = health?.chroma?.available === true;
  const ollamaOk = (state.llmStatus || health?.ollama)?.available === true;
  return `<div class="system-row"><span>API</span><span class="system-value"><i class="status-dot ${apiOk ? "ok" : "bad"}"></i>${apiOk ? "Online" : "Offline"}</span></div>
    <div class="system-row"><span>Chroma</span><span class="system-value"><i class="status-dot ${chromaOk ? "ok" : apiOk ? "warn" : "bad"}"></i>${chromaOk ? "Ready" : apiOk ? "Unavailable" : "Unknown"}</span></div>
    <div class="system-row"><span>Ollama</span><span class="system-value"><i class="status-dot ${ollamaOk ? "ok" : apiOk ? "warn" : "bad"}"></i>${ollamaOk ? "Ready" : apiOk ? "Unavailable" : "Unknown"}</span></div>`;
}

function updateSystemCard() {
  const card = document.querySelector(".system-card");
  if (card) card.innerHTML = systemCardHtml();
}

function currentContext() {
  const f = activeFile(),
    r = selectedRecord();
  if (state.view === "record" && r)
    return { kicker: r.record_id || "Record", title: r.work || "Record", meta: f?.name || "" };
  const map = {
    home: [
      "Overview",
      "Dashboard",
      "Workspace, vector stores, review activity, and corpus statistics",
    ],
    list: [
      "Corpora",
      f?.name || "Records",
      f ? `${f.records.length.toLocaleString()} ${tr("dynamic.records")}` : "Open a JSONL file",
    ],
    works: ["Corpora", "Works", "Cross-file work overview"],
    global: ["Corpora", "Global Search", "Search and filter every loaded record"],
    annotations: [
      "Corpora",
      "Annotations",
      "Review annotations by work or in recent-activity order",
    ],
    semanticmap: ["Corpora", "Semantic map", "Concepts, topics, and persons that occur together"],
    pdf: [
      "Corpus Management",
      state.pdf.title || "Corpus Builder",
      state.pdf.name
        ? `${state.pdf.name} · page ${state.pdf.page}`
        : "Build, monitor, and review auditable corpus records",
    ],
    compare: ["Corpora", "Record Comparison", "Inspect field and text differences"],
    vector: ["Corpus Management", "Corpus Data", "Persistent local ChromaDB collections"],
    rag: [
      "Research",
      "Research",
      "Run the evidence-grounded DerridAI retrieval and synthesis pipeline",
    ],
    faq: [
      "Research",
      "Response Library",
      "Browse saved RAG questions, answers, evidence, reruns, and grades",
    ],
    responsecache: [
      "System",
      "System Data",
      "Inspect application storage, trace derived metadata, and manage saved research responses.",
    ],
    providers: [
      "AI & Automation",
      "LLM Providers",
      "Create, configure, test, warm, and reuse LLM provider profiles across every LLM workflow",
    ],
    config: [
      "System",
      "Settings",
      "Application behavior, retrieval defaults, storage, backup, and reset controls",
    ],
  };
  const dynamicTitle =
    (state.view === "list" && f?.name) || (state.view === "pdf" && state.pdf.title);
  const dynamicMeta = (state.view === "list" && f) || (state.view === "pdf" && state.pdf.name);
  const key = map[state.view] ? state.view : "list";
  const [kickerText, titleText, metaText] = map[key];
  // Static labels are translated; data-driven titles (file names, PDF titles) are not.
  return {
    kicker: tr(`context.${key}.kicker`, kickerText),
    title: dynamicTitle ? titleText : tr(`context.${key}.title`, titleText),
    meta: dynamicMeta ? metaText : tr(`context.${key}.meta`, metaText),
  };
}

const uid = () => crypto.randomUUID();
const clearFileDerivedState = (fileId) => clearFileDerivedStateOf(state, fileId);

// Corpus-derived data is read far more often than it changes. Keep one flattened
// index and memoized derived values instead of rebuilding thousands of row
// wrapper objects on every render/chart/filter pass. Any persisted corpus edit
// invalidates the cache synchronously.
const {
  openMixedWorkValuesDialog,
  openWorkMetadataEditor,
  openWorkMetadataLlmDialog,
  openWorkMetadataProposalResult,
  openRemoveWorkModal,
  openSeparateWorksModal,
} = createWorkDialogs({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api: (...args) => api(...args),
  applyRecordChanges: (...args) => applyRecordChanges(...args),
  clearFileDerivedState: (...args) => clearFileDerivedState(...args),
  cloneAuditValue: (...args) => cloneAuditValue(...args),
  corpusCache,
  decorateDisabledControls: (...args) => decorateDisabledControls(...args),
  display: (...args) => display(...args),
  jobLabel: (...args) => jobLabel(...args),
  label: (...args) => label(...args),
  navigateTo: (...args) => navigateTo(...args),
  parseProposedMetadataValue: (...args) => parseProposedMetadataValue(...args),
  parseWorkMetadataValue: (...args) => parseWorkMetadataValue(...args),
  persistFileNow: (...args) => persistFileNow(...args),
  persistPrefs: (...args) => persistPrefs(...args),
  providerProfile: (...args) => providerProfile(...args),
  providerProfiles: (...args) => providerProfiles(...args),
  providerRequestConfig: (...args) => providerRequestConfig(...args),
  recordStores: (...args) => recordStores(...args),
  refreshStores: (...args) => refreshStores(...args),
  renderView: (...args) => renderView(...args),
  representativeWorkMetadata: (...args) => representativeWorkMetadata(...args),
  shell: (...args) => shell(...args),
  showAppModal: (...args) => showAppModal(...args),
  startJobPolling,
  syncJobProgressToasts,
  tr: (...args) => tr(...args),
  trf: (...args) => trf(...args),
  uid: (...args) => uid(...args),
  uniqueWorkValues: (...args) => uniqueWorkValues(...args),
  workIndex: (...args) => workIndex(...args),
  workMetadataControlSpec: (...args) => workMetadataControlSpec(...args),
});
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
function viewDisabledReason(view) {
  if (!canAccessPage(view)) return "This workspace is available to administrators only.";
  if (view === "vector" && isResearcher() && !hasChromaService()) return dbUnavailableReason();
  if (view === "faq" && !hasChromaService())
    return "ChromaDB is unavailable, so the Response Library cannot be opened.";
  return "";
}

const {
  openMergeDialog,
  openBulkFieldEditor,
  openOcrCleanupDialog,
  openEditor,
  openStoreRecordEditor,
  openRecordHistoryBrowser,
  openUpsertQueue,
} = recordDialogs;

const idbGetAll = workspaceDb.getAll;
const idbGet = workspaceDb.get;
const idbPut = workspaceDb.put;
const idbDelete = workspaceDb.remove;
function serializableFile(file) {
  return serializableRecordsFile(file);
}

function responseCacheStore() {
  return state.stores.find(isResponseCacheStore) || null;
}

// Names of the facts shown for an operation (panel rows and the details dialog), translated at render time.

// ---- Operations panel bridge -------------------------------------------------------------
// The panel itself is a Vue component (components/OperationsPanel.vue). The runtime still owns
// job state, the dock, toasts, and the details/results dialogs, so the panel reads a plain view
// model from here and calls back into the existing functions.

function relativeTime(value) {
  return relativeTimeLabel(value, Date.now(), { tr, trf, locale: state.translations?.locale });
}

// 0.36.10 native Search bridge. SearchView owns presentation while the runtime
// continues to own browser-local corpus state, Chroma transport, evidence
// selection, URL serialization, and the existing LLM review workflows.

/** @param {{field?: string, op?: string, value?: string}} [options] */

function cleanRecord(f, i) {
  const c = stripLigaturesAndArtifacts(f.records[i].text);
  if (!c.changed) return toast(tr("runtime.toast.no_ligatures"), { tone: "warning" });
  const changed = applyRecordChanges(f, i, { text: c.text }, { source: "ocr_cleanup" });
  shell();
  renderView();
  toast(
    trf(
      changed === 1
        ? "runtime.toast.tracked_changes_applied_one"
        : "runtime.toast.tracked_changes_applied_many",
      {
        count: changed,
      },
    ),
    { tone: "success" },
  );
}

async function currentPdfPageText() {
  const result = await extractPdfPageSmart(state.pdf.page);
  state.pdf.text = result.text;
  state.pdf.extractionSource = result.source;
  state.pdf.extractError = result.warning || "";
  return result.text || "";
}
async function applyPdfLinkMatch(match) {
  if (!match?.key)
    return openMessageDialog({
      title: "No supported record match",
      message: match?.reason || "The model did not identify a sufficiently supported record.",
    });
  const item = reviewItemFromKey(match.key);
  if (!item)
    return openMessageDialog({
      title: "Matched record unavailable",
      message: "The matched record is no longer loaded.",
      tone: "danger",
    });
  const confidence = Number(match.confidence);
  const approved = await openMessageDialog({
    title: "Link PDF page to record?",
    message: `PDF page ${state.pdf.page} → ${item.record.record_id || "matched record"}\n\n${Number.isFinite(confidence) ? `${Math.round(confidence * 100)}% confidence` : "Confidence not reported"}${match.reason ? `\n${match.reason}` : ""}`,
    confirmLabel: "Link page",
    cancelLabel: "Cancel",
  });
  if (!approved) return;
  linkPdfPage(item.file, item.index, state.pdf.page);
  toast(
    trf("runtime.toast.linked_page", {
      page: state.pdf.page,
      record: item.record.record_id || tr("dynamic.record_one"),
    }),
    { tone: "success" },
  );
}
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

function rankPdfLinkCandidates(rawText) {
  const titleTokens = new Set(
    String(state.pdf.title || state.pdf.name || "")
      .toLocaleLowerCase()
      .split(/\W+/)
      .filter((token) => token.length > 3),
  );
  const page = Number(state.pdf.page);
  const pageTokens = new Set(
    String(rawText || "")
      .toLocaleLowerCase()
      .split(/\W+/)
      .filter((token) => token.length > 5)
      .slice(0, 140),
  );
  return allRows()
    .map(({ file, record, index }) => {
      let score = 0;
      const work = String(record.work || record.document_title || "").toLocaleLowerCase();
      score +=
        work.split(/\W+/).filter((token) => token.length > 3 && titleTokens.has(token)).length * 6;
      const start = Number(record.page_start),
        end = Number(record.page_end ?? record.page_start);
      if (
        Number.isFinite(start) &&
        Number.isFinite(end) &&
        page >= Math.min(start, end) &&
        page <= Math.max(start, end)
      )
        score += 10;
      if (pdfLinks(record).some((link) => link.pdf_file === state.pdf.name)) score += 12;
      score += Math.min(
        12,
        String(record.text || "")
          .toLocaleLowerCase()
          .split(/\W+/)
          .filter((token) => token.length > 5 && pageTokens.has(token))
          .slice(0, 140).length,
      );
      return {
        score,
        candidate: {
          key: reviewKey(file, index),
          record_id: record.record_id || "",
          work: record.work || "",
          pages: pages(record),
          citation: record.inline_citation || record.full_citation || "",
          text: String(record.text || "").slice(0, 600),
        },
      };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, 32)
    .map((item) => item.candidate);
}
async function cleanPdfPageWithLlm() {
  try {
    const raw_text = await currentPdfPageText();
    if (!raw_text.trim()) return toast(tr("runtime.toast.no_page_text"), { tone: "warning" });
    openLlmTaskLauncher({
      task: "pdf_clean_text",
      title: "Clean PDF page text",
      description: `${state.pdf.title || state.pdf.name} · page ${state.pdf.page}`,
      payload: {
        mode: "clean_text",
        raw_text,
        pdf_file: state.pdf.name || null,
        pdf_title: state.pdf.title || null,
        pdf_author: state.pdf.author || null,
        pdf_page: state.pdf.page,
        candidates: [],
      },
      onForegroundResult: async (result) => {
        state.pdf.text = result.text || "";
        state.pdf.extractionSource = `LLM cleanup · ${result.model || "model"} · page ${state.pdf.page}`;
        state.pdf.extractError = "";
        window.dispatchEvent(new CustomEvent("derridai:pdf-explorer-refresh"));
      },
    });
  } catch (error) {
    toast(trf("runtime.toast.llm_cleanup_prepare_failed", { detail: error.message }), {
      tone: "danger",
    });
  }
}
async function draftPdfPageWithLlm() {
  try {
    const raw_text = await currentPdfPageText();
    if (!raw_text.trim()) return toast(tr("runtime.toast.no_page_text"), { tone: "warning" });
    openLlmTaskLauncher({
      task: "pdf_draft_record",
      title: "Create draft record from PDF page",
      description: `${state.pdf.title || state.pdf.name} · page ${state.pdf.page}`,
      payload: {
        mode: "draft_record",
        raw_text,
        pdf_file: state.pdf.name || null,
        pdf_title: state.pdf.title || null,
        pdf_author: state.pdf.author || null,
        pdf_page: state.pdf.page,
        candidates: [],
      },
      onForegroundResult: async (result) => openPdfDraftRecord(result.record || {}),
    });
  } catch (error) {
    toast(trf("runtime.toast.draft_prepare_failed", { detail: error.message }), { tone: "danger" });
  }
}
async function linkPdfPageWithLlm() {
  if (!state.files.length)
    return toast(tr("runtime.toast.load_before_pdf_match"), { tone: "warning" });
  try {
    const raw_text = await currentPdfPageText(),
      candidates = rankPdfLinkCandidates(raw_text);
    if (!candidates.length)
      return toast(tr("runtime.toast.no_candidate_records"), { tone: "warning" });
    openLlmTaskLauncher({
      task: "pdf_link_record",
      title: "Link PDF page to record",
      description: `${state.pdf.title || state.pdf.name} · page ${state.pdf.page} · ${candidates.length} pre-ranked candidates`,
      payload: {
        mode: "link_record",
        raw_text,
        pdf_file: state.pdf.name || null,
        pdf_title: state.pdf.title || null,
        pdf_author: state.pdf.author || null,
        pdf_page: state.pdf.page,
        candidates,
      },
      onForegroundResult: async (result) => applyPdfLinkMatch(result.match || {}),
    });
  } catch (error) {
    toast(trf("runtime.toast.record_matching_prepare_failed", { detail: error.message }), {
      tone: "danger",
    });
  }
}

function recordOptionForKey(key) {
  const item = lookupRecord(key);
  if (!item) return null;
  return { value: key, label: recordOptionLabel(item.file, item.record, item.index) };
}

async function refreshStoreWorks(force = false) {
  if (!state.activeStore) {
    state.storeWorks = [];
    state.storeWorkStats = [];
    state.storeWorksStore = "";
    state.storeWork = "";
    return;
  }
  if (!force && state.storeWorksStore === state.activeStore) return;
  const data = await api(`/api/stores/${encodeURIComponent(state.activeStore)}/works`);
  state.storeWorks = data.works || [];
  state.storeWorkStats = data.stats || state.storeWorks.map((work) => ({ work, count: null }));
  state.storeWorksStore = state.activeStore;
  if (state.storeWork && !state.storeWorks.includes(state.storeWork)) state.storeWork = "";
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

function translatedNavLabel(item) {
  const keys = {
    home: "nav.dashboard",
    list: "nav.records",
    record: "nav.record",
    works: "nav.works",
    global: "nav.search",
    annotations: "nav.annotations",
    semanticmap: "nav.semantic_map",
    pdf: "nav.pdf",
    compare: "nav.compare",
    vector: "nav.vector",
    rag: "nav.rag",
    faq: "nav.faq",
    responsecache: "runtime.system_data",
    providers: "nav.providers",
    schemas: "nav.schemas",
    config: "nav.config",
  };
  return keys[item.id] ? tr(keys[item.id], item.label) : item.label;
}
function translatedSectionLabel(section) {
  const keys = {
    Overview: "section.overview",
    Corpus: "section.corpora",
    Corpora: "section.corpora",
    Research: "section.research",
    Tools: "section.corpus_management",
    Build: "section.corpus_management",
    "Corpus Management": "section.corpus_management",
    "AI & Automation": "section.ai_automation",
    System: "section.system",
  };
  return keys[section] ? tr(keys[section], section) : section;
}
function getShellSnapshot() {
  const ctx = currentContext();
  const totalLoaded = allRows().length;
  const flagged = needsReviewItems().length;
  const pending = state.activeStore ? pendingUpsertRows().length : 0;
  const corpusStores = recordStores();
  const dbRecords = corpusStores.reduce((sum, store) => sum + (Number(store.count) || 0), 0);
  const cacheCount = Number(responseCacheStore()?.count || 0);
  const activeJobs = state.jobs.filter((job) =>
    ["queued", "running", "cancelling"].includes(job.status),
  ).length;
  return {
    view: state.view,
    files: state.files.map((file) => describeRecordsFile(file, state.activeFileId)),
    context: ctx,
    totalLoaded,
    flagged,
    pending,
    activeJobs,
    corpusStoreCount: corpusStores.length,
    dbRecords,
    cacheCount,
    hasCorpusDb: hasCorpusDb(),
    dbUnavailableReason: dbUnavailableReason(),
    activeStore: state.activeStore,
    canEdit: canUse("editLocalRecords") && state.view === "record" && Boolean(selectedRecord()),
    selectedEvidenceCount: selectedEvidenceEntries().length,
    systemHtml: systemCardHtml(),
    nav: getNavItems(),
  };
}
// Navigation membership depends only on the signed-in user, the static view list,
// and translations, never on workspace/bootstrap state. The Vue shell calls this as
// soon as a user exists so the menu is complete before the slow runtime bootstrap.
function getNavItems() {
  return viewConfig
    .filter((item) => canAccessPage(item.id))
    .map((item) => ({
      ...item,
      label:
        item.id === "home"
          ? tr("nav.home")
          : isResearcher() && item.id === "vector"
            ? tr("research.corpus_search")
            : translatedNavLabel(item),
      section: translatedSectionLabel(item.section),
      disabledReason: viewDisabledReason(item.id),
    }));
}

function toggleSidebar() {
  state.sidebarCollapsed = !state.sidebarCollapsed;
  persistPrefs();
  shell();
}
function triggerBulkEdit() {
  return canUse("editLocalRecords")
    ? openBulkFieldEditor()
    : toast(tr("runtime.toast.cannot_edit_records"), { tone: "warning" });
}
function triggerOcrClean() {
  return canUse("editLocalRecords")
    ? openOcrCleanupDialog()
    : toast(tr("runtime.toast.cannot_edit_records"), { tone: "warning" });
}
function triggerReviewFlagged() {
  return canUse("editLocalRecords")
    ? openTouchup(needsReviewItems())
    : toast(tr("runtime.toast.cannot_review_records"), { tone: "warning" });
}
function triggerAutoImproveFlagged() {
  return canUse("editLocalRecords")
    ? openTouchup(needsReviewItems(), "auto")
    : toast(tr("runtime.toast.cannot_modify_records"), { tone: "warning" });
}
function triggerUpsertQueue() {
  return canUse("manageCorpus")
    ? openUpsertQueue()
    : toast(tr("runtime.toast.cannot_manage_dbs"), { tone: "warning" });
}
function triggerEdit() {
  return canUse("editLocalRecords")
    ? openEditor()
    : toast(tr("runtime.toast.cannot_edit_records"), { tone: "warning" });
}

let chartTooltip = null;
function ensureChartTooltip() {
  if (chartTooltip?.isConnected) return chartTooltip;
  chartTooltip = document.createElement("div");
  chartTooltip.className = "chart-hover-tooltip";
  document.body.appendChild(chartTooltip);
  return chartTooltip;
}
document.addEventListener("pointermove", (event) => {
  const target = event.target.closest?.("[data-chart-tip]");
  if (!target) {
    if (chartTooltip) chartTooltip.classList.remove("show");
    return;
  }
  const tip = ensureChartTooltip();
  tip.textContent = target.dataset.chartTip || "";
  tip.style.left = `${Math.min(window.innerWidth - 280, event.clientX + 14)}px`;
  tip.style.top = `${Math.max(8, event.clientY + 14)}px`;
  tip.classList.add("show");
});

window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => {
  if (e.dataTransfer?.files?.length) {
    e.preventDefault();
    if (!isResearcher())
      importFiles(
        [...e.dataTransfer.files].filter((f) => /\.(jsonl|ndjson|json|zst)$/i.test(f.name)),
      );
  }
});
document.addEventListener(
  "click",
  (event) => {
    const resultButton = event.target.closest?.(
      "[data-toast-open-result],[data-job-result],[data-rag-job-result],[data-recent-rag-result]",
    );
    if (!resultButton) return;
    const jobId =
      resultButton.dataset.toastOpenResult ||
      resultButton.dataset.jobResult ||
      resultButton.dataset.ragJobResult ||
      resultButton.dataset.recentRagResult;
    if (!jobId) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    resultButton.disabled = true;
    const original = resultButton.innerHTML;
    resultButton.textContent = "Opening…";
    void openJobResults(jobId)
      .catch((error) =>
        openMessageDialog({
          title: "Could not open operation result",
          message: error.message || String(error),
          tone: "danger",
        }),
      )
      .finally(() => {
        if (resultButton.isConnected) {
          resultButton.disabled = false;
          resultButton.innerHTML = original;
        }
      });
  },
  { capture: true },
);

document.addEventListener("click", (event) => {
  const loadedButton = event.target.closest("[data-copy-row-key]");
  if (loadedButton) {
    event.stopPropagation();
    const item = reviewItemFromKey(loadedButton.dataset.copyRowKey);
    if (item)
      copyJsonToClipboard(
        item.file.records[item.index],
        item.record.record_id || tr("dynamic.record_one"),
      );
    else toast(tr("runtime.toast.source_record_gone"), { tone: "danger" });
    return;
  }
  const citeButton = event.target.closest("[data-cite-row-key]");
  if (citeButton) {
    event.stopPropagation();
    const item = reviewItemFromKey(citeButton.dataset.citeRowKey);
    if (item) copyCitation(item.record, citeButton.dataset.citeKind || "inline");
    return;
  }
  const dbCite = event.target.closest("[data-admin-db-cite],[data-r-cite]");
  if (dbCite) {
    event.preventDefault();
    event.stopPropagation();
    const id = String(dbCite.dataset.adminDbId || dbCite.dataset.rId || "");
    const result = (state.storeSearchResults || []).find(
      (item) => String(item.id || item.record?._chroma_id || item.record?.record_id || "") === id,
    );
    const record =
      result?.record ||
      (state.storeRecords || []).find(
        (item) => String(item._chroma_id || item.record_id || "") === id,
      );
    if (record)
      copyCitation(record, dbCite.dataset.adminDbCite || dbCite.dataset.rCite || "inline");
    else toast(tr("runtime.toast.citation_source_gone"), { tone: "warning" });
    return;
  }
  const evidenceButton = event.target.closest("[data-toggle-workspace-evidence]");
  if (evidenceButton) {
    event.stopPropagation();
    const item = reviewItemFromKey(evidenceButton.dataset.toggleWorkspaceEvidence);
    if (item) {
      toggleWorkspaceEvidence(item.file, item.index);
      renderView();
    }
    return;
  }
  const storeButton = event.target.closest("[data-copy-store-record]");
  if (storeButton) {
    event.stopPropagation();
    const record = state.storeRecords.find(
      (item) => String(item._chroma_id || "") === String(storeButton.dataset.copyStoreRecord || ""),
    );
    if (record) {
      const copy = { ...record };
      delete copy._chroma_id;
      copyJsonToClipboard(copy, copy.record_id || tr("runtime.toast.chroma_record"));
    }
  }
});
let researcherPolicy = { ready: false, blocked: new Set(), contextual: [] };
let researcherPolicyToastAt = 0;
async function researcherTokenDigest(value) {
  if (!globalThis.crypto?.subtle) return "";
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(normalizeResearcherToken(value)),
  );
  return Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, "0")).join("");
}
async function refreshResearcherContentPolicy() {
  if (!state.userContext) {
    researcherPolicy = { ready: false, blocked: new Set(), contextual: [] };
    return;
  }
  try {
    const data = await api("/api/i18n/content-policy");
    researcherPolicy = {
      ready: Boolean(data?.ready),
      blocked: new Set(Array.isArray(data?.blocked_term_hashes) ? data.blocked_term_hashes : []),
      contextual: Array.isArray(data?.contextual) ? data.contextual : [],
    };
  } catch {
    researcherPolicy = { ready: false, blocked: new Set(), contextual: [] };
  }
}
async function filterResearcherInputElement(target) {
  if (!isResearcher() || !(target instanceof HTMLElement) || !researcherPolicy.ready) return;
  const acceptsText =
    target instanceof HTMLTextAreaElement ||
    (target instanceof HTMLInputElement &&
      ["text", "search", "url", "email", "tel"].includes(target.type)) ||
    target.isContentEditable;
  if (!acceptsText) return;
  const original = target.isContentEditable ? target.textContent || "" : target.value || "";
  const words = [...original.matchAll(/[\w'’]+/g)];
  const remove = [];
  for (const match of words) {
    const raw = match[0];
    const digest = await researcherTokenDigest(raw);
    if (!digest) continue;
    if (researcherPolicy.blocked.has(digest)) {
      remove.push(raw);
      continue;
    }
    const rule = researcherPolicy.contextual.find((item) => item.term_hash === digest);
    if (!rule) continue;
    if (
      rule.allow_title_case &&
      raw === raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase() &&
      raw !== raw.toLowerCase()
    )
      continue;
    const index = words.indexOf(match);
    const surrounding = words
      .slice(Math.max(0, index - 3), index + 4)
      .map((item) => normalizeResearcherToken(item[0]))
      .join(" ");
    if (
      (rule.allow_if_surrounding || []).some((marker) =>
        surrounding.includes(normalizeResearcherToken(marker)),
      )
    )
      continue;
    const before = normalizeResearcherToken(
      original.slice(Math.max(0, match.index - 20), match.index),
    );
    if (
      (rule.allow_if_before_markers || []).some((marker) =>
        before.includes(normalizeResearcherToken(marker)),
      )
    )
      continue;
    remove.push(raw);
  }
  if (!remove.length) return;
  let filtered = original;
  for (const token of remove)
    filtered = filtered.replace(
      new RegExp(`\\b${token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`),
      "",
    );
  filtered = filtered.replace(/ {2,}/g, " ");
  if (target.isContentEditable) target.textContent = filtered;
  else target.value = filtered;
  target.dispatchEvent(new Event("change", { bubbles: true }));
  const now = Date.now();
  if (now - researcherPolicyToastAt > 1200) {
    researcherPolicyToastAt = now;
    toast(tr("content_filter.warning"), { tone: "warning" });
  }
}
document.addEventListener(
  "input",
  (event) => {
    void filterResearcherInputElement(event.target);
  },
  true,
);

/**
 * Re-derive runtime view state from the browser location (the router owns the URL) and repaint.
 * Used by browser back/forward and whenever a router navigation settles somewhere the runtime did not expect.
 */
function syncFromLocation() {
  applyUrlState();
  repaintAfterLocationChange();
}
/** Persist and repaint after the shared URL state has been applied (by the runtime or by the router). */
function repaintAfterLocationChange() {
  persistPrefs();
  shell();
  renderView();
}
/** The runtime view a path belongs to, or undefined for paths with no legacy view. */
function viewForPath(path) {
  return viewFromPath(path);
}

let metadataSearchDelegationWired = false;
function wireMetadataSearchDelegation() {
  if (metadataSearchDelegationWired) return;
  metadataSearchDelegationWired = true;
  document.addEventListener(
    "click",
    (event) => {
      const button =
        event.target instanceof Element
          ? event.target.closest("[data-meta-search-field][data-meta-search-value]")
          : null;
      if (!button) return;
      if (button.closest("#main")) {
        event.preventDefault();
        event.stopPropagation();
        searchByMetadata(button.dataset.metaSearchField, button.dataset.metaSearchValue, {
          contains: button.dataset.metaSearchContains === "true",
        });
      }
    },
    true,
  );
}
let tabScrollPreservationWired = false;
function wireTabScrollPreservation() {
  if (tabScrollPreservationWired) return;
  tabScrollPreservationWired = true;
  const selector = [
    '[role="tab"]',
    ".view-tab",
    ".db-browser-tab",
    ".search-mode-tabs button",
    ".dashboard-search-tabs button",
    ".annotation-tabs button",
    ".annotations-tabs button",
    ".record-view-tabs button",
    ".compare-tabs button",
    ".config-tabs button",
  ].join(",");
  const arm = (target) => {
    if (!target) return;
    const top = window.scrollY,
      left = window.scrollX,
      main = document.querySelector("#main");
    let cancelled = false,
      quietTimer = null,
      stopTimer = null,
      observer = null;
    const restore = () => {
      if (cancelled) return;
      if (Math.abs(window.scrollY - top) > 1 || Math.abs(window.scrollX - left) > 1)
        window.scrollTo({ top, left, behavior: "auto" });
    };
    const stop = () => {
      observer?.disconnect();
      if (quietTimer) clearTimeout(quietTimer);
      if (stopTimer) clearTimeout(stopTimer);
      window.removeEventListener("wheel", cancel);
      window.removeEventListener("touchmove", cancel);
    };
    const cancel = () => {
      cancelled = true;
      stop();
    };
    observer = main
      ? new MutationObserver(() => {
          restore();
          if (quietTimer) clearTimeout(quietTimer);
          quietTimer = setTimeout(stop, 140);
        })
      : null;
    observer?.observe(main, { childList: true, subtree: true });
    window.addEventListener("wheel", cancel, { passive: true, once: true });
    window.addEventListener("touchmove", cancel, { passive: true, once: true });
    requestAnimationFrame(restore);
    stopTimer = setTimeout(stop, 1200);
  };
  document.addEventListener(
    "pointerdown",
    (event) => {
      const target = event.target instanceof Element ? event.target.closest(selector) : null;
      if (target) arm(target);
    },
    true,
  );
  document.addEventListener(
    "keydown",
    (event) => {
      if (!["Enter", " "].includes(event.key)) return;
      const target = event.target instanceof Element ? event.target.closest(selector) : null;
      if (target) arm(target);
    },
    true,
  );
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

export {
  operationViewModel,
  operationDetailPairs,
  jobProgressText,
  state,
  viewConfig,
  setUserContext,
  setTranslationDictionary,
  getShellSnapshot,
  setShellRefreshHook,
  setUrlSyncHook,
  syncFromLocation,
  repaintAfterLocationChange,
  viewForPath,
  refreshJobs,
  unmountOperationsPanel,
  viewPathMap,
  pathViewMap,
  bootstrapRuntime,
  renderView,
  toggleSidebar,
  activateFile,
  triggerBulkEdit,
  triggerOcrClean,
  triggerReviewFlagged,
  triggerAutoImproveFlagged,
  openTouchup,
  touchupWorkspaceInfo,
  touchupProviderStatus,
  touchupRequestConfig,
  touchupRequest,
  touchupSubmitBackground,
  touchupApplyResults,
  triggerUpsertQueue,
  triggerEdit,
  getProviderProfilesForUi,
  getProviderRequestConfigForUi,
  getDefaultProviderProfileId,
  getProviderStatusesForUi,
  getProviderWarmupsForUi,
  saveProviderProfilesForUi,
  addProviderProfileForUi,
  removeProviderProfileForUi,
  setDefaultProviderProfileForUi,
  testProviderProfileForUi,
  warmProviderProfileForUi,
  registerExternalJob,
  dbUnavailableReason,
  hasCorpusDb,
  notifyVectorStoresChanged,
  openCollectionCreationWizard,
  upsertRows,
  persistPrefs,
  lookupRecord,
  copyJsonToClipboard,
  copyCitation,
  formatTimestamp,
  responseCacheStore,
  dashboardTotals,
  activeFile,
  allLinkedRowsForLoadedPdf,
  cleanPdfPageWithLlm,
  draftPdfPageWithLlm,
  evidenceIsSelected,
  linkPdfPage,
  linkPdfPageWithLlm,
  linkedPdfRows,
  loadedPdfPagesForRecord,
  pages,
  pdfDisplayTitle,
  recordOptionForKey,
  reviewKey,
  searchRecordOptions,
  selectedIndex,
  selectedRecord,
  shell,
  tr,
  unlinkPdfLink,
  workspaceEvidenceSelectionKey,
  renderPdfCanvas,
  extractPdfPageSmart,
  extractPdfAllSmart,
  dashboardRecordPreview,
  dashboardWorkspaceRecordTarget,
  openSharedAnnotationRecord,
  dashboardMetricBody,
  pieShareSeries,
  workInsightMetrics,
  recentAnnotations,
  recentAuditChanges,
  recordStores,
  refreshServerAnnotations,
  refreshStoreWorks,
  renderCorpusBuildsHomeCard,
  renderOperationsPanel,
  searchByMetadata,
  mountOperationsPanelHost,
  wireCorpusBuildsHomeCard,
  workIndex,
  dbSearchWhere,
  isResearcher,
  hasCapability,
  canAccessPage,
  syncUrl,
  navigateTo,
  uid,
  openJobResults,
  api,
  label,
  flushWorkspacePrefs,
  applyAppearance,
  clearAllUpdates,
  pendingUpsertRows,
  decorateDisabledControls,
  translateLegacyDom,
  getResearchWorkspaceSnapshot,
  updateResearchConfig,
  removeResearchEvidence,
  clearResearchEvidence,
  discoverResearchModels,
  refreshResearchJobs,
  getResearchJob,
  cancelResearchJob,
  deleteResearchJob,
  startResearchRun,
  gradeResearchJob,
  prepareResearchRerun,
  getResponseFaqPage,
  gradeResponseFaqRecord,
  rerunResponseFaqRecord,
  getRecordWorkspaceSnapshot,
  getRecordObjectGraph,
  getDerridaiNormativeModel,
  recordWorkspaceNavigate,
  setRecordWorkspaceFind,
  toggleCurrentRecordEvidence,
  toggleCurrentRecordReviewSelection,
  copyCurrentRecordCitation,
  copyCurrentRecordJson,
  saveCurrentRecordChanges,
  addCurrentRecordAnnotation,
  replyToCurrentAnnotation,
  removeCurrentRecordAnnotation,
  currentRecordPrimaryAction,
  searchCurrentRecordMetadata,
  navigateRecordWorkspace,
  getWorksWorkspaceSnapshot,
  setWorksSearch,
  setWorksOverview,
  setWorksView,
  setWorksStore,
  syncWork,
  syncAllWorks,
  openWorkMetadataEditorForVue as openWorkMetadataEditor,
  openWorkMetadataLlmDialogForVue as openWorkMetadataLlmDialog,
  loadAnnotationsWorkspace,
  setAnnotationsWorkspaceQuery,
  setAnnotationsWorkspaceView,
  openAnnotationsWorkspaceRecord,
  openAnnotationsWorkspaceWork,
  removeAnnotationsWorkspaceItem,
  openWorkAnnotations,
  getNavItems,
  getWarmOnStartForUi,
  setWarmOnStartForUi,
  prepareWorksWorkspace,
  searchWorkRecords,
  searchWorkOverview,
  populateAllWorksMetadata,
  inspectWorksMixedField,
  searchWorksInsight,
  reviewFlaggedWork,
  autoImproveWork,
  removeEntireWork,
  browseResearcherWork,
  openSeparateWorksModal,
  getSearchWorkspaceSnapshot,
  setSearchScope,
  updateSearchQuery,
  setSearchAdvancedOpen,
  setSearchMethod,
  setSearchStore,
  setSearchMmrOptions,
  setSearchLayout,
  setSearchPage,
  setSearchPageSize,
  setSearchColumns,
  setSearchSort,
  toggleSearchFacet,
  clearSearchFacetFilters,
  clearSearchAllFilters,
  addSearchAdvancedFilter,
  removeSearchAdvancedFilter,
  runSearchWorkspace,
  searchResultAction,
  setSearchResultSelected,
  setSearchPageSelected,
  clearSearchSelection,
  runSearchSelectionAction,
  getSearchShareHref,
  restoreSearchViewFromHref,
  getRecordsListSnapshot,
  setRecordsListQuery,
  setRecordsListStore,
  setRecordsListPage,
  setRecordsListPageSize,
  setRecordsListSort,
  setRecordsListFilter,
  clearRecordsListFilters,
  setRecordsListRowSelected,
  setRecordsListPageSelected,
  selectRecordsListMatches,
  clearRecordsListSelection,
  openRecordsListRecord,
  copyRecordsListJson,
  copyRecordsListCitation,
  toggleRecordsListEvidence,
  setRecordsListColumns,
  resetRecordsListColumns,
  getRecordsListShareHref,
  recordsListCommand,
};
