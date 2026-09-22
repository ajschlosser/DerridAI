/* Copyright 2026 Aaron John Schlosser, PhD. */
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
import { cloneAuditValue, compareValues, computeRecordFingerprint, sameValue, sortRows } from "../domain/recordValues";
import { compressUrlState, decompressUrlState } from "../domain/urlState";
import { countOccurrences, flattenValueList, parseJsonl, subsetRuleMatches, subsetValueText, valueMatches } from "../domain/recordQuery";
import { DB_NAME, createWorkspaceDb, deleteAllDerridaiBrowserState as deleteAllDerridaiBrowserStateCompat } from "../services/workspaceDb";
import { finiteResearchNumber, normalizedResearchConfig, researchEvidenceForUi, researchJobForUi, researchProfileForUi, sanitizeResearchGeneration } from "../domain/researchPayloads";
import { fullCitation, inlineCitation, mlaAuthorName, mlaPageSpan, mlaSentence } from "../domain/citations";
import { describeRecordsFile, serializableRecordsFile } from "../domain/recordsFiles";
import {
  applyAppearance as applyAppearanceCompat,
  applyUiTheme as applyUiThemeCompat,
  setTranslationDictionary as setTranslationDictionaryCompat,
  syncColorScheme as syncColorSchemeCompat,
  tr as trCompat,
  trf as trfCompat,
  translateDynamicUiValue as translateDynamicUiValueCompat,
  translateLegacyDom as translateLegacyDomCompat,
} from "./legacyCompat.js";
import { TOUCHUP_CREATABLE_FIELDS, TOUCHUP_GROUPS, WORK_METADATA_LLM_FIELDS } from "../domain/runtimeConstants";
import { FIELD_LABELS, SEARCH_AUTOCOMPLETE_EXCLUDED, SEARCH_FACET_FIELDS, SEARCH_FILTER_FIELDS, SEARCH_LOADED_COLUMNS, TABLE_DEFAULTS, viewConfig } from "../domain/runtimeConstants";
import { esc, icon } from "../domain/html";
import { annotationMatches, jsonPretty, llmDiffSides, ragAnswerHtml, reviewDiffSides } from "../domain/reviewPresentation";
import { touchupFieldsForRecord } from "../domain/touchupFields";
import { commonWorkValue, representativeWorkMetadata, workCoverUrl, workOverviewMetadataRows } from "../domain/workMetadata";
import { compactRecordHistory, normalizePdfLinkChanges, pdfLinks, recordPayload } from "../domain/recordPayloads";
import { highlight, highlightTerms, modelOptionLabel, openAiModelMatchesKind, semanticSimilarity, snippet } from "../domain/recordFormatting";
import { fullHttpErrorDetail } from "../domain/httpErrors";
import { parsePastedRecord } from "../domain/pastedRecord";
import { providerRequestConfig } from "../domain/providerRequest";
import { recordHistoryVersions, upsertAuditDelta } from "../domain/recordHistory";
import { barChart, lineChart, multiLineChart, pieChart, statList } from "../domain/dashboardCharts";
import { createOperationPresenters } from "../domain/operationPresenters";
import { createFieldFormatting } from "../domain/fieldFormatting";
import { createCorpusAnalytics } from "../domain/corpusAnalytics";
import { createSearchFacets } from "../domain/searchFacets";
import { createRecordPresenters } from "../domain/recordPresenters";
import { createProviderProfiles } from "../domain/providerProfilesService";
import { createSearchWorkspace } from "../domain/searchWorkspace";
import { createRecordsWorkspace } from "../domain/recordsWorkspace";
import { createRecordWorkspace } from "../domain/recordWorkspace";
import { createWorksWorkspace } from "../domain/worksWorkspace";
import { createJobsWorkspace } from "../domain/jobsWorkspace";
import { createDashboardRenderer } from "../domain/dashboardRenderer";
import { createResponseCacheRenderer } from "../domain/responseCacheRenderer";
import { createPdfExplorerRenderer } from "../domain/pdfExplorerRenderer";
import { createJobDialogs } from "../domain/jobDialogs";
import { createWorkDialogs } from "../domain/workDialogs";
import { createRecordDialogs } from "../domain/recordDialogs";
import { createOperationDock } from "../domain/operationDock";
import { createBackupWorkspace } from "../domain/backupWorkspace";
import { createResearchWorkspace } from "../domain/researchWorkspace";
import { createAnnotationsWorkspace } from "../domain/annotationsWorkspace";
import { subscribeToJobChanges, touchJobs } from "../state/jobsState";
import { touchCorpus } from "../state/workspaceState";
import { createRuntimeState } from "./runtimeState";
import { createVectorCollectionBridge } from "./vectorCollectionBridge";

pdfjsLib.GlobalWorkerOptions.workerPort = new PdfWorker();

const state = createRuntimeState();

function syncColorScheme(){
  return syncColorSchemeCompat(state);
}
function applyUiTheme(theme){
  return applyUiThemeCompat(state, theme);
}
function applyAppearance(patch={}){
  return applyAppearanceCompat(state, patch);
}

function setTranslationDictionary(locale,dictionary={},base={},info={}){
  return setTranslationDictionaryCompat(state, locale, dictionary, base, info);
}
function tr(key,fallback=""){
  return trCompat(state, key, fallback);
}
function trf(key,fallback,values={}){
  return trfCompat(state, key, fallback, values);
}
function translateDynamicUiValue(value){
  return translateDynamicUiValueCompat(state, value);
}
function translateLegacyDom(root=document.querySelector("#main")){
  return translateLegacyDomCompat(state, root);
}

const {workIndex,dateKeys,topNeedsReviewWorkSeries,needsReviewTimeline,topFieldValues,publicationYearSeries,workRecordShares,averageRecordLengthForTopWorks,recentAuditChanges}=createCorpusAnalytics({allRows,memoCorpus});
const {label,display,normalizeRagGrade,parseBulkFieldValue,parseWorkMetadataValue}=createFieldFormatting({tr});
const {searchFacetRawValues,searchFacetDisplay,searchFacetMatches,searchRowMatchesFacets,searchRecordMatchesFacets,searchFacetCountsFromRows,searchFacetCountsFromRecords,buildSearchFacets,searchSuggestions,searchFilterDescriptor,dbSearchFilterDescriptors,searchColumnOptions,searchSimilarity,searchMatchReasons,rowMatchesListFilters}=createSearchFacets({
  tr,label,display,recordDbStatus,pages,recordFields,uid:()=>uid(),dbSearchWhere,filterOpsForField,
  getSearchFacetFilters:()=>state.searchFacetFilters,
});
const {
    uniqueWorkValues,
    normalizedRecordAnnotation,
    workInsightPieHtml,
    flattenedMetricValues,
    topRecordFieldShare,
    topRecordFieldValues,
    workInsightMetrics,
    mixedWorkValueButton,
    workMetadataControl,
    workInsightsPanelHtml,
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
    recordOptionLabel,
    ragGradeEvidencePayload,
  }=createRecordPresenters({
  tr,trf,pages,recordDbStatus,label,display,
  allAnnotations:()=>allAnnotations(),
  compareSearchIndex:()=>compareSearchIndex(),
});
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
  }=createProviderProfiles({
  state,api,persistPrefs,isResearcher,
  uid:()=>uid(),
  warmupProviderProfile:(...args)=>warmupProviderProfile(...args),
});
const {localSearchBaseRows,searchScope,searchLayout,searchResultFromKey,buildWorkspaceSearchResult,buildDatabaseSearchResult,sortDatabaseSearchResults,getSearchWorkspaceSnapshot,setSearchScope,updateSearchQuery,setSearchAdvancedOpen,setSearchMethod,setSearchStore,setSearchMmrOptions,setSearchLayout,setSearchPage,setSearchPageSize,setSearchColumns,setSearchSort,toggleSearchFacet,clearSearchFacetFilters,clearSearchAllFilters,addSearchAdvancedFilter,removeSearchAdvancedFilter,runSearchWorkspace,searchResultAction,setSearchResultSelected,setSearchPageSelected,clearSearchSelection,runSearchSelectionAction,getSearchShareHref,restoreSearchViewFromHref,safeDbSearchWhere,researcherDbRecords}=createSearchWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allRows:(...args)=>allRows(...args),
  api:(...args)=>api(...args),
  applyCompressedTableUrlState:(...args)=>applyCompressedTableUrlState(...args),
  buildSearchFacets:(...args)=>buildSearchFacets(...args),
  canAccessPage:(...args)=>canAccessPage(...args),
  canUse:(...args)=>canUse(...args),
  clearReviewSelection:(...args)=>clearReviewSelection(...args),
  copyCitation:(...args)=>copyCitation(...args),
  dbEvidenceKey:(...args)=>dbEvidenceKey(...args),
  dbSearchFilterDescriptors:(...args)=>dbSearchFilterDescriptors(...args),
  dbSearchWhere:(...args)=>dbSearchWhere(...args),
  evidenceIsSelected:(...args)=>evidenceIsSelected(...args),
  filterOpsForField:(...args)=>filterOpsForField(...args),
  getTableColumns:(...args)=>getTableColumns(...args),
  hasCapability:(...args)=>hasCapability(...args),
  isResearcher:(...args)=>isResearcher(...args),
  label:(...args)=>label(...args),
  navigateTo:(...args)=>navigateTo(...args),
  openBulkFieldEditor:(...args)=>openBulkFieldEditor(...args),
  openDatabaseCreationFromResearch:(...args)=>openDatabaseCreationFromResearch(...args),
  openStoreRecordEditor:(...args)=>openStoreRecordEditor(...args),
  openTouchup:(...args)=>openTouchup(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  recordDbStatus:(...args)=>recordDbStatus(...args),
  recordStores:(...args)=>recordStores(...args),
  refreshPresenceForRows:(...args)=>refreshPresenceForRows(...args),
  refreshStores:(...args)=>refreshStores(...args),
  reviewItemFromKey:(...args)=>reviewItemFromKey(...args),
  reviewKey:(...args)=>reviewKey(...args),
  searchColumnOptions:(...args)=>searchColumnOptions(...args),
  searchFilterDescriptor:(...args)=>searchFilterDescriptor(...args),
  searchMatchReasons:(...args)=>searchMatchReasons(...args),
  searchRecordMatchesFacets:(...args)=>searchRecordMatchesFacets(...args),
  searchRowMatchesFacets:(...args)=>searchRowMatchesFacets(...args),
  searchSimilarity:(...args)=>searchSimilarity(...args),
  searchSuggestions:(...args)=>searchSuggestions(...args),
  selectedEvidenceEntries:(...args)=>selectedEvidenceEntries(...args),
  selectedReviewItems:(...args)=>selectedReviewItems(...args),
  setReviewSelected:(...args)=>setReviewSelected(...args),
  shell:(...args)=>shell(...args),
  syncUrl:(...args)=>syncUrl(...args),
  tableAvailableFields:(...args)=>tableAvailableFields(...args),
  toast:(...args)=>toast(...args),
  toggleDbEvidence:(...args)=>toggleDbEvidence(...args),
  toggleSort:(...args)=>toggleSort(...args),
  toggleWorkspaceEvidence:(...args)=>toggleWorkspaceEvidence(...args),
  tr:(...args)=>tr(...args),
  uid:(...args)=>uid(...args),
  urlFromState:(...args)=>urlFromState(...args),
  workspaceEvidenceSelectionKey:(...args)=>workspaceEvidenceSelectionKey(...args),
});
const {clearRecordsListFilters,clearRecordsListSelection,copyRecordsListCitation,copyRecordsListJson,getRecordsListShareHref,getRecordsListSnapshot,openRecordsListRecord,recordsListCommand,resetRecordsListColumns,selectRecordsListMatches,setRecordsListColumns,setRecordsListFilter,setRecordsListPage,setRecordsListPageSelected,setRecordsListPageSize,setRecordsListQuery,setRecordsListRowSelected,setRecordsListSort,setRecordsListStore,toggleRecordsListEvidence}=createRecordsWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  activeFile:(...args)=>activeFile(...args),
  canUse:(...args)=>canUse(...args),
  clearReviewSelection:(...args)=>clearReviewSelection(...args),
  copyCitation:(...args)=>copyCitation(...args),
  copyJsonToClipboard:(...args)=>copyJsonToClipboard(...args),
  dbUnavailableReason:(...args)=>dbUnavailableReason(...args),
  evidenceIsSelected:(...args)=>evidenceIsSelected(...args),
  getTableColumns:(...args)=>getTableColumns(...args),
  hasCapability:(...args)=>hasCapability(...args),
  hasCorpusDb:(...args)=>hasCorpusDb(...args),
  label:(...args)=>label(...args),
  navigateTo:(...args)=>navigateTo(...args),
  needsReviewItems:(...args)=>needsReviewItems(...args),
  openBulkFieldEditor:(...args)=>openBulkFieldEditor(...args),
  openOcrCleanupDialog:(...args)=>openOcrCleanupDialog(...args),
  openTouchup:(...args)=>openTouchup(...args),
  pageInfo:(...args)=>pageInfo(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  recordDbStatus:(...args)=>recordDbStatus(...args),
  recordStores:(...args)=>recordStores(...args),
  recordsListCell:(...args)=>recordsListCell(...args),
  refreshPresenceForRows:(...args)=>refreshPresenceForRows(...args),
  reviewKey:(...args)=>reviewKey(...args),
  rowMatchesListFilters:(...args)=>rowMatchesListFilters(...args),
  rowsFromReviewSelection:(...args)=>rowsFromReviewSelection(...args),
  selectedReviewItems:(...args)=>selectedReviewItems(...args),
  setActiveStore:(...args)=>setActiveStore(...args),
  setListFilterValue:(...args)=>setListFilterValue(...args),
  setReviewSelected:(...args)=>setReviewSelected(...args),
  shell:(...args)=>shell(...args),
  syncUrl:(...args)=>syncUrl(...args),
  tableAvailableFields:(...args)=>tableAvailableFields(...args),
  toast:(...args)=>toast(...args),
  toggleSort:(...args)=>toggleSort(...args),
  toggleWorkspaceEvidence:(...args)=>toggleWorkspaceEvidence(...args),
  tr:(...args)=>tr(...args),
  upsertRows:(...args)=>upsertRows(...args),
  urlFromState:(...args)=>urlFromState(...args),
  workspaceEvidenceSelectionKey:(...args)=>workspaceEvidenceSelectionKey(...args),
});
const {recordWorkspaceRecord,researcherCurrentRecord,getRecordWorkspaceSnapshot,recordWorkspaceNavigate,setRecordWorkspaceFind,toggleCurrentRecordEvidence,toggleCurrentRecordReviewSelection,copyCurrentRecordCitation,copyCurrentRecordJson,saveCurrentRecordChanges,addCurrentRecordAnnotation,removeCurrentRecordAnnotation,currentRecordPrimaryAction,searchCurrentRecordMetadata,navigateRecordWorkspace}=createRecordWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  activeFile:(...args)=>activeFile(...args),
  api:(...args)=>api(...args),
  applyRecordChanges:(...args)=>applyRecordChanges(...args),
  canAccessPage:(...args)=>canAccessPage(...args),
  canUse:(...args)=>canUse(...args),
  cleanRecord:(...args)=>cleanRecord(...args),
  copyJsonToClipboard:(...args)=>copyJsonToClipboard(...args),
  dbEvidenceKey:(...args)=>dbEvidenceKey(...args),
  evidenceIsSelected:(...args)=>evidenceIsSelected(...args),
  hasCapability:(...args)=>hasCapability(...args),
  hasCorpusDb:(...args)=>hasCorpusDb(...args),
  isResearcher:(...args)=>isResearcher(...args),
  linkPdfPage:(...args)=>linkPdfPage(...args),
  loadStorePage:(...args)=>loadStorePage(...args),
  loadedPdfPagesForRecord:(...args)=>loadedPdfPagesForRecord(...args),
  navigateTo:(...args)=>navigateTo(...args),
  normalizedRecordAnnotation:(...args)=>normalizedRecordAnnotation(...args),
  openLoadedPdfPage:(...args)=>openLoadedPdfPage(...args),
  openPdfExplorerWorkspace:(...args)=>openPdfExplorerWorkspace(...args),
  openRecordHistoryBrowser:(...args)=>openRecordHistoryBrowser(...args),
  openTouchup:(...args)=>openTouchup(...args),
  pdfDisplayTitle:(...args)=>pdfDisplayTitle(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  refreshServerAnnotations:(...args)=>refreshServerAnnotations(...args),
  refreshStores:(...args)=>refreshStores(...args),
  researcherDbRecords:(...args)=>researcherDbRecords(...args),
  reviewKey:(...args)=>reviewKey(...args),
  searchByMetadata:(...args)=>searchByMetadata(...args),
  selectedIndex:(...args)=>selectedIndex(...args),
  selectedRecord:(...args)=>selectedRecord(...args),
  setReviewSelected:(...args)=>setReviewSelected(...args),
  shell:(...args)=>shell(...args),
  syncUrl:(...args)=>syncUrl(...args),
  toast:(...args)=>toast(...args),
  toggleDbEvidence:(...args)=>toggleDbEvidence(...args),
  toggleWorkspaceEvidence:(...args)=>toggleWorkspaceEvidence(...args),
  tr:(...args)=>tr(...args),
  uid:(...args)=>uid(...args),
  unlinkAllPdfLinks:(...args)=>unlinkAllPdfLinks(...args),
  unlinkPdfLink:(...args)=>unlinkPdfLink(...args),
  upsertRows:(...args)=>upsertRows(...args),
  workspaceEvidenceKey:(...args)=>workspaceEvidenceKey(...args),
});
const {describeAdminWork,worksSnapshotBase,prepareWorksWorkspace,getWorksWorkspaceSnapshot,setWorksSearch,setWorksOverview,setWorksStore,syncWork,syncAllWorks,searchWorkRecords,searchWork,searchWorkOverview,openWorkMetadataEditorForVue,openWorkMetadataLlmDialogForVue,openWorkAnnotations,populateAllWorksMetadata,inspectWorksMixedField,searchWorksInsight,reviewFlaggedWork,autoImproveWork,removeEntireWork,browseResearcherWork}=createWorksWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allAnnotations:(...args)=>allAnnotations(...args),
  canUse:(...args)=>canUse(...args),
  dbUnavailableReason:(...args)=>dbUnavailableReason(...args),
  describeResearcherWork:(...args)=>describeResearcherWork(...args),
  display:(...args)=>display(...args),
  hasCorpusDb:(...args)=>hasCorpusDb(...args),
  isResearcher:(...args)=>isResearcher(...args),
  label:(...args)=>label(...args),
  navigateTo:(...args)=>navigateTo(...args),
  needsReviewItems:(...args)=>needsReviewItems(...args),
  openMixedWorkValuesDialog:(...args)=>openMixedWorkValuesDialog(...args),
  openRemoveWorkModal:(...args)=>openRemoveWorkModal(...args),
  openTouchup:(...args)=>openTouchup(...args),
  openWorkMetadataEditor:(...args)=>openWorkMetadataEditor(...args),
  openWorkMetadataLlmDialog:(...args)=>openWorkMetadataLlmDialog(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  providerProfiles:(...args)=>providerProfiles(...args),
  recordStores:(...args)=>recordStores(...args),
  refreshPresenceForRows:(...args)=>refreshPresenceForRows(...args),
  refreshServerAnnotations:(...args)=>refreshServerAnnotations(...args),
  refreshStoreWorks:(...args)=>refreshStoreWorks(...args),
  refreshStores:(...args)=>refreshStores(...args),
  searchByMetadata:(...args)=>searchByMetadata(...args),
  setActiveStore:(...args)=>setActiveStore(...args),
  syncUrl:(...args)=>syncUrl(...args),
  tr:(...args)=>tr(...args),
  uid:(...args)=>uid(...args),
  uniqueWorkValues:(...args)=>uniqueWorkValues(...args),
  upsertRows:(...args)=>upsertRows(...args),
  workDbStatus:(...args)=>workDbStatus(...args),
  workIndex:(...args)=>workIndex(...args),
  workInsightMetrics:(...args)=>workInsightMetrics(...args),
  worksBiblioValue:(...args)=>worksBiblioValue(...args),
});
const {refreshJobs,startJobPolling,pauseRuntime,pruneClientJobState,removeFinishedJob,clearFinishedOperations,syncUpsertJobReceipts,cancelBackgroundJob,submitBackgroundLlmJob,registerExternalJob,maybeDesktopNotify,syncJobProgressToasts}=createJobsWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  announceOperationDock:(...args)=>announceOperationDock(...args),
  api:(...args)=>api(...args),
  ensureJobProgressCard:(...args)=>ensureJobProgressCard(...args),
  jobLabel:(...args)=>jobLabel(...args),
  jobProviderSummary:(...args)=>jobProviderSummary(...args),
  navigateTo:(...args)=>navigateTo(...args),
  notifyOperationsChanged:(...args)=>notifyOperationsChanged(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  recordFingerprint:(...args)=>recordFingerprint(...args),
  refreshCorpusBuildsHomeCardOnly:(...args)=>refreshCorpusBuildsHomeCardOnly(...args),
  refreshOperationsPanelOnly:(...args)=>refreshOperationsPanelOnly(...args),
  refreshRagProgressPanel:(...args)=>refreshRagProgressPanel(...args),
  refreshStores:(...args)=>refreshStores(...args),
  reviewItemFromKey:(...args)=>reviewItemFromKey(...args),
  reviewKey:(...args)=>reviewKey(...args),
  shell:(...args)=>shell(...args),
  toast:(...args)=>toast(...args),
  touchupRecordPayload:(...args)=>touchupRecordPayload(...args),
  trf:(...args)=>trf(...args),
  updateDbStatusElements:(...args)=>updateDbStatusElements(...args),
  updateOperationStackCount:(...args)=>updateOperationStackCount(...args),
});
const {backupContainsCredentials,downloadFullBackup,restoreFullBackup}=createBackupWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  deleteWorkspaceDatabase:(...args)=>deleteWorkspaceDatabase(...args),
  idbPut:(...args)=>idbPut(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  persistFileNow:(...args)=>persistFileNow(...args),
  providerProfiles:(...args)=>providerProfiles(...args),
  serializableFile:(...args)=>serializableFile(...args),
  toast:(...args)=>toast(...args),
  workspacePrefs:(...args)=>workspacePrefs(...args),
});
const {openSharedAnnotationRecord,dashboardTotals,dashboardWorkspaceRecordTarget,dashboardRecordPreview,renderDashboard}=createDashboardRenderer({
  state,
  openAnnotationsWorkspaceRecord:(...args)=>openAnnotationsWorkspaceRecord(...args),
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allRows:(...args)=>allRows(...args),
  api:(...args)=>api(...args),
  applyUiTheme:(...args)=>applyUiTheme(...args),
  canAccessPage:(...args)=>canAccessPage(...args),
  compactNumber:(...args)=>compactNumber(...args),
  dashboardMetricBody:(...args)=>dashboardMetricBody(...args),
  dbSearchWhere:(...args)=>dbSearchWhere(...args),
  decorateDisabledControls:(...args)=>decorateDisabledControls(...args),
  defaultProviderProfile:(...args)=>defaultProviderProfile(...args),
  formatTimestamp:(...args)=>formatTimestamp(...args),
  hasCapability:(...args)=>hasCapability(...args),
  isResearcher:(...args)=>isResearcher(...args),
  label:(...args)=>label(...args),
  memoCorpus:(...args)=>memoCorpus(...args),
  mountOperationsPanelHost:(...args)=>mountOperationsPanelHost(...args),
  navigateTo:(...args)=>navigateTo(...args),
  openDatabaseCreationFromResearch:(...args)=>openDatabaseCreationFromResearch(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  pieShareSeries:(...args)=>pieShareSeries(...args),
  providerDisplayName:(...args)=>providerDisplayName(...args),
  recentAnnotations:(...args)=>recentAnnotations(...args),
  recentAuditChanges:(...args)=>recentAuditChanges(...args),
  recordStores:(...args)=>recordStores(...args),
  refreshServerAnnotations:(...args)=>refreshServerAnnotations(...args),
  refreshStoreWorks:(...args)=>refreshStoreWorks(...args),
  refreshStores:(...args)=>refreshStores(...args),
  relativeTime:(...args)=>relativeTime(...args),
  renderCorpusBuildsHomeCard:(...args)=>renderCorpusBuildsHomeCard(...args),
  renderOperationsPanel:(...args)=>renderOperationsPanel(...args),
  researcherDbRecords:(...args)=>researcherDbRecords(...args),
  responseCacheStore:(...args)=>responseCacheStore(...args),
  searchByMetadata:(...args)=>searchByMetadata(...args),
  syncUrl:(...args)=>syncUrl(...args),
  toast:(...args)=>toast(...args),
  tr:(...args)=>tr(...args),
  trf:(...args)=>trf(...args),
  uid:(...args)=>uid(...args),
  wireCorpusBuildsHomeCard:(...args)=>wireCorpusBuildsHomeCard(...args),
  workIndex:(...args)=>workIndex(...args),
  workInsightMetrics:(...args)=>workInsightMetrics(...args),
});
const {toast,applyOperationStackPosition,setOperationDockMinimized,announceOperationDock,operationDockCardStats,wireOperationStackDrag,progressStack,updateOperationStackCount,showOperationProgress,updateOperationProgress,hideOperationProgress,ensureJobProgressCard}=createOperationDock({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  cancelBackgroundJob:(...args)=>cancelBackgroundJob(...args),
  clearFinishedOperations:(...args)=>clearFinishedOperations(...args),
  jobLabel:(...args)=>jobLabel(...args),
  jobProgressText:(...args)=>jobProgressText(...args),
  jobProviderSummary:(...args)=>jobProviderSummary(...args),
  openJobDetails:(...args)=>openJobDetails(...args),
  openJobResults:(...args)=>openJobResults(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  removeFinishedJob:(...args)=>removeFinishedJob(...args),
  tr:(...args)=>tr(...args),
  translateDynamicUiValue:(...args)=>translateDynamicUiValue(...args),
  trf:(...args)=>trf(...args),
  uid:(...args)=>uid(...args),
});
const {openJobDetails,openJobResults,openRagResult,openReviewRecordPreview,openLlmToolResult,openLlmTaskLauncher,openPdfDraftRecord,openTouchup}=createJobDialogs({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api:(...args)=>api(...args),
  applyPdfLinkMatch:(...args)=>applyPdfLinkMatch(...args),
  applyRecordChanges:(...args)=>applyRecordChanges(...args),
  canAccessPage:(...args)=>canAccessPage(...args),
  cancelBackgroundJob:(...args)=>cancelBackgroundJob(...args),
  cloneAuditValue:(...args)=>cloneAuditValue(...args),
  formatTimestamp:(...args)=>formatTimestamp(...args),
  fullCitation:(...args)=>fullCitation(...args),
  isResearcher:(...args)=>isResearcher(...args),
  jobLabel:(...args)=>jobLabel(...args),
  jsonPretty:(...args)=>jsonPretty(...args),
  label:(...args)=>label(...args),
  navSnapshot:(...args)=>navSnapshot(...args),
  navigateTo:(...args)=>navigateTo(...args),
  normalizeTouchupItems:(...args)=>normalizeTouchupItems(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  openWorkMetadataProposalResult:(...args)=>openWorkMetadataProposalResult(...args),
  pages:(...args)=>pages(...args),
  persistFileNow:(...args)=>persistFileNow(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  providerDisplayName:(...args)=>providerDisplayName(...args),
  providerProfile:(...args)=>providerProfile(...args),
  providerProfiles:(...args)=>providerProfiles(...args),
  providerRequestConfig:(...args)=>providerRequestConfig(...args),
  pruneClientJobState:(...args)=>pruneClientJobState(...args),
  ragGradeHtml:(...args)=>ragGradeHtml(...args),
  recordFingerprint:(...args)=>recordFingerprint(...args),
  recordStores:(...args)=>recordStores(...args),
  refreshJobs:(...args)=>refreshJobs(...args),
  refreshRagProgressPanel:(...args)=>refreshRagProgressPanel(...args),
  refreshStores:(...args)=>refreshStores(...args),
  renderPdf:(...args)=>renderPdf(...args),
  renderView:(...args)=>renderView(...args),
  reviewDiffSides:(...args)=>reviewDiffSides(...args),
  reviewItemFromKey:(...args)=>reviewItemFromKey(...args),
  reviewKey:(...args)=>reviewKey(...args),
  sanitizeResearchGeneration:(...args)=>sanitizeResearchGeneration(...args),
  shell:(...args)=>shell(...args),
  shellRefreshHook:(...args)=>shellRefreshHook(...args),
  showAppModal:(...args)=>showAppModal(...args),
  startJobPolling:(...args)=>startJobPolling(...args),
  syncJobProgressToasts:(...args)=>syncJobProgressToasts(...args),
  toast:(...args)=>toast(...args),
  tr:(...args)=>tr(...args),
  uid:(...args)=>uid(...args),
  upsertRecordPayload:(...args)=>upsertRecordPayload(...args),
  getUrlSyncHook:()=>urlSyncHook,
  warmupProviderProfile:(...args)=>warmupProviderProfile(...args),
});
const {renderPdf,renderPdfCanvas,extractPdfPageBrowser,extractPdfApi,extractPdfPageSmart,extractPdfAllSmart}=createPdfExplorerRenderer({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  activeFile:(...args)=>activeFile(...args),
  allLinkedRowsForLoadedPdf:(...args)=>allLinkedRowsForLoadedPdf(...args),
  cleanPdfPageWithLlm:(...args)=>cleanPdfPageWithLlm(...args),
  defaultProviderProfile:(...args)=>defaultProviderProfile(...args),
  draftPdfPageWithLlm:(...args)=>draftPdfPageWithLlm(...args),
  evidenceIsSelected:(...args)=>evidenceIsSelected(...args),
  linkPdfPage:(...args)=>linkPdfPage(...args),
  linkPdfPageWithLlm:(...args)=>linkPdfPageWithLlm(...args),
  linkedPdfRows:(...args)=>linkedPdfRows(...args),
  loadPdfMetadata:(...args)=>loadPdfMetadata(...args),
  loadedPdfPagesForRecord:(...args)=>loadedPdfPagesForRecord(...args),
  lookupRecord:(...args)=>lookupRecord(...args),
  navigateTo:(...args)=>navigateTo(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  pages:(...args)=>pages(...args),
  pdfDisplayTitle:(...args)=>pdfDisplayTitle(...args),
  persistCurrentPdfAsset:(...args)=>persistCurrentPdfAsset(...args),
  providerDisplayName:(...args)=>providerDisplayName(...args),
  recordOptionForKey:(...args)=>recordOptionForKey(...args),
  recordOptionLabel:(...args)=>recordOptionLabel(...args),
  renderView:(...args)=>renderView(...args),
  reviewKey:(...args)=>reviewKey(...args),
  searchRecordOptions:(...args)=>searchRecordOptions(...args),
  selectedIndex:(...args)=>selectedIndex(...args),
  selectedRecord:(...args)=>selectedRecord(...args),
  shell:(...args)=>shell(...args),
  syncUrl:(...args)=>syncUrl(...args),
  toast:(...args)=>toast(...args),
  tr:(...args)=>tr(...args),
  unlinkPdfLink:(...args)=>unlinkPdfLink(...args),
  workspaceEvidenceSelectionKey:(...args)=>workspaceEvidenceSelectionKey(...args),
});
const {renderResponseCache}=createResponseCacheRenderer({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api:(...args)=>api(...args),
  formatTimestamp:(...args)=>formatTimestamp(...args),
  navigateTo:(...args)=>navigateTo(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  refreshStores:(...args)=>refreshStores(...args),
  responseCacheStore:(...args)=>responseCacheStore(...args),
  showViewLoading:(...args)=>showViewLoading(...args),
  toast:(...args)=>toast(...args),
});
const {researchConfigForUi,getResearchWorkspaceSnapshot,updateResearchConfig,removeResearchEvidence,clearResearchEvidence,discoverResearchModels,refreshResearchJobs,getResearchJob,cancelResearchJob,deleteResearchJob,generationFromProfile,startResearchRun,gradeResearchJob,prepareResearchRerun,getResponseFaqPage,gradeResponseFaqRecord,rerunResponseFaqRecord,rememberRagPrompt,rememberRagRun,prepareRagRerun}=createResearchWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api:(...args)=>api(...args),
  canAccessPage:(...args)=>canAccessPage(...args),
  cancelBackgroundJob:(...args)=>cancelBackgroundJob(...args),
  clearSelectedEvidence:(...args)=>clearSelectedEvidence(...args),
  gradeRagResponse:(...args)=>gradeRagResponse(...args),
  hasCapability:(...args)=>hasCapability(...args),
  hasCorpusDb:(...args)=>hasCorpusDb(...args),
  isResearcher:(...args)=>isResearcher(...args),
  navigateTo:(...args)=>navigateTo(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  providerDisplayName:(...args)=>providerDisplayName(...args),
  providerProfile:(...args)=>providerProfile(...args),
  providerProfiles:(...args)=>providerProfiles(...args),
  pruneClientJobState:(...args)=>pruneClientJobState(...args),
  recordStores:(...args)=>recordStores(...args),
  refreshJobs:(...args)=>refreshJobs(...args),
  refreshStores:(...args)=>refreshStores(...args),
  selectedEvidenceEntries:(...args)=>selectedEvidenceEntries(...args),
  selectedEvidencePayload:(...args)=>selectedEvidencePayload(...args),
  setEvidence:(...args)=>setEvidence(...args),
  shellRefreshHook:(...args)=>shellRefreshHook(...args),
  startJobPolling:(...args)=>startJobPolling(...args),
  syncJobProgressToasts:(...args)=>syncJobProgressToasts(...args),
  toast:(...args)=>toast(...args),
  tr:(...args)=>tr(...args),
  uid:(...args)=>uid(...args),
});
const {serverAnnotationItems,refreshServerAnnotations,allAnnotations,recentAnnotations,annotationTimeline,getAnnotationsWorkspaceSnapshot,annotationWorkspaceItem,loadAnnotationsWorkspace,setAnnotationsWorkspaceQuery,setAnnotationsWorkspaceView,openAnnotationsWorkspaceRecord,openAnnotationsWorkspaceWork,removeAnnotationsWorkspaceItem}=createAnnotationsWorkspace({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allRows:(...args)=>allRows(...args),
  api:(...args)=>api(...args),
  applyRecordChanges:(...args)=>applyRecordChanges(...args),
  canUse:(...args)=>canUse(...args),
  dateKeys:(...args)=>dateKeys(...args),
  hasCapability:(...args)=>hasCapability(...args),
  isResearcher:(...args)=>isResearcher(...args),
  label:(...args)=>label(...args),
  memoCorpus:(...args)=>memoCorpus(...args),
  navigateTo:(...args)=>navigateTo(...args),
  notifyToast:(...args)=>notifyToast(...args),
  persistFileNow:(...args)=>persistFileNow(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  recordStores:(...args)=>recordStores(...args),
  refreshStores:(...args)=>refreshStores(...args),
  reviewItemFromKey:(...args)=>reviewItemFromKey(...args),
  reviewKey:(...args)=>reviewKey(...args),
  syncUrl:(...args)=>syncUrl(...args),
  tr:(...args)=>tr(...args),
});
const {jobLabel,jobProviderSummary,jobElapsedSeconds,humanDuration,fact,decisionLabel,operationIcon,operationResultKind,operationSubtitle,jobProgressText,operationDetailPairs,operationViewModel}=createOperationPresenters({
  tr,trf,
  getLocale:()=>state.translations?.locale||"en-US",
  getStores:()=>state.stores,
  providerProfiles:()=>providerProfiles(),
  providerDisplayName:profile=>providerDisplayName(profile),
});






function systemCardHtml(){
  const health=state.health;
  if(!health){
    return `<div class="system-row"><span>API</span><span class="system-value"><i class="status-dot warn"></i>Checking</span></div>
      <div class="system-row"><span>Chroma</span><span class="system-value"><i class="status-dot"></i>Unknown</span></div>
      <div class="system-row"><span>Ollama</span><span class="system-value"><i class="status-dot"></i>Unknown</span></div>`;
  }
  const apiOk=health?.ok===true;
  const chromaOk=health?.chroma?.available===true;
  const ollamaOk=(state.llmStatus||health?.ollama)?.available===true;
  return `<div class="system-row"><span>API</span><span class="system-value"><i class="status-dot ${apiOk?"ok":"bad"}"></i>${apiOk?"Online":"Offline"}</span></div>
    <div class="system-row"><span>Chroma</span><span class="system-value"><i class="status-dot ${chromaOk?"ok":apiOk?"warn":"bad"}"></i>${chromaOk?"Ready":apiOk?"Unavailable":"Unknown"}</span></div>
    <div class="system-row"><span>Ollama</span><span class="system-value"><i class="status-dot ${ollamaOk?"ok":apiOk?"warn":"bad"}"></i>${ollamaOk?"Ready":apiOk?"Unavailable":"Unknown"}</span></div>`;
}

function updateSystemCard(){
  const card=document.querySelector(".system-card");
  if(card)card.innerHTML=systemCardHtml();
}

function currentContext(){
  const f=activeFile(),r=selectedRecord();
  if(state.view==="record"&&r) return {kicker:r.record_id||"Record", title:r.work||"Record", meta:f?.name||""};
  const map={
    home:["Overview","Dashboard","Workspace, vector stores, review activity, and corpus statistics"],
    list:["Corpus",f?.name||"Records",f?`${f.records.length.toLocaleString()} ${tr("dynamic.records","records")}`:"Open a JSONL file"],
    works:["Corpus","Works","Cross-file work overview"],
    global:["Corpus","Global Search","Search and filter every loaded record"],
    annotations:["Corpus","Annotations","Review annotations by work or in recent-activity order"],
    pdf:["Tools",state.pdf.title||"Corpus Builder",state.pdf.name?`${state.pdf.name} · page ${state.pdf.page}`:"Build auditable records or inspect source PDFs"],
    compare:["Tools","Record Comparison","Inspect field and text differences"],
    vector:["Storage","Vector Stores","Persistent local ChromaDB collections"],
    rag:["Research","Research","Run the evidence-grounded DerridAI retrieval and synthesis pipeline"],
    faq:["Research","Response Library","Browse saved RAG questions, answers, evidence, reruns, and grades"],
    responsecache:["Research","Response Cache","Manage cached RAG queries, answers, evidence, and LLM grades separately from corpus vector stores"],
    providers:["System","LLM Providers","Create, configure, test, warm, and reuse LLM provider profiles across every LLM workflow"],
    config:["System","Settings","Application behavior, retrieval defaults, storage, backup, and reset controls"],
  };
  const dynamicTitle=state.view==="list"&&f?.name||state.view==="pdf"&&state.pdf.title;
  const dynamicMeta=state.view==="list"&&f||state.view==="pdf"&&state.pdf.name;
  const key=map[state.view]?state.view:"list";
  const [kickerText,titleText,metaText]=map[key];
  // Static labels are translated; data-driven titles (file names, PDF titles) are not.
  return {
    kicker:tr(`context.${key}.kicker`,kickerText),
    title:dynamicTitle?titleText:tr(`context.${key}.title`,titleText),
    meta:dynamicMeta?metaText:tr(`context.${key}.meta`,metaText),
  };
}

const uid = () => crypto.randomUUID();
async function stableJsonlFileIdentity(text){
  // Shareable URLs can only point back to a browser-local JSONL workspace if
  // the same corpus file resolves to the same identifier on every client. Use
  // a content digest rather than a random tab id. The JSONL payload is already
  // resident as text during import, so hashing does not add another file read.
  const bytes=new TextEncoder().encode(String(text||""));
  const digest=await crypto.subtle.digest("SHA-256",bytes);
  const hex=[...new Uint8Array(digest)].map(value=>value.toString(16).padStart(2,"0")).join("");
  return {id:`jsonl-${hex.slice(0,24)}`,content_hash:hex};
}
const activeFile = () => state.files.find(f => f.id === state.activeFileId) || null;
const selectedIndex = f => Math.max(0, Math.min((f?.records.length || 1)-1, state.selected[f?.id] ?? 0));
const selectedRecord = () => {
  const f = activeFile();
  return f?.records[selectedIndex(f)] || null;
};

// Corpus-derived data is read far more often than it changes. Keep one flattened
// index and memoized derived values instead of rebuilding thousands of row
// wrapper objects on every render/chart/filter pass. Any persisted corpus edit
// invalidates the cache synchronously.
const corpusCache={rows:null,fields:null,memo:new Map(),version:0};
const {openMixedWorkValuesDialog,openWorkMetadataEditor,openWorkMetadataLlmDialog,openWorkMetadataProposalResult,openRemoveWorkModal,openSeparateWorksModal}=createWorkDialogs({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api:(...args)=>api(...args),
  applyRecordChanges:(...args)=>applyRecordChanges(...args),
  clearFileDerivedState:(...args)=>clearFileDerivedState(...args),
  cloneAuditValue:(...args)=>cloneAuditValue(...args),
  corpusCache,
  decorateDisabledControls:(...args)=>decorateDisabledControls(...args),
  display:(...args)=>display(...args),
  jobLabel:(...args)=>jobLabel(...args),
  label:(...args)=>label(...args),
  navigateTo:(...args)=>navigateTo(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  parseProposedMetadataValue:(...args)=>parseProposedMetadataValue(...args),
  parseWorkMetadataValue:(...args)=>parseWorkMetadataValue(...args),
  persistFileNow:(...args)=>persistFileNow(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  providerProfile:(...args)=>providerProfile(...args),
  providerProfiles:(...args)=>providerProfiles(...args),
  providerRequestConfig:(...args)=>providerRequestConfig(...args),
  recordStores:(...args)=>recordStores(...args),
  refreshStores:(...args)=>refreshStores(...args),
  renderDashboard:(...args)=>renderDashboard(...args),
  renderView:(...args)=>renderView(...args),
  representativeWorkMetadata:(...args)=>representativeWorkMetadata(...args),
  shell:(...args)=>shell(...args),
  showAppModal:(...args)=>showAppModal(...args),
  startJobPolling:(...args)=>startJobPolling(...args),
  syncJobProgressToasts:(...args)=>syncJobProgressToasts(...args),
  toast:(...args)=>toast(...args),
  tr:(...args)=>tr(...args),
  trf:(...args)=>trf(...args),
  uid:(...args)=>uid(...args),
  uniqueWorkValues:(...args)=>uniqueWorkValues(...args),
  workIndex:(...args)=>workIndex(...args),
  workMetadataControl:(...args)=>workMetadataControl(...args),
  workflowProviderSelectHtml:(...args)=>workflowProviderSelectHtml(...args),
  workflowProviderSummaryHtml:(...args)=>workflowProviderSummaryHtml(...args),
});
let recordFingerprintCache=new WeakMap();
function invalidateCorpusCache(){
  touchCorpus();
  corpusCache.rows=null;
  corpusCache.fields=null;
  corpusCache.memo.clear();
  corpusCache.version++;
  // Fingerprints are cached by record object identity, but records are edited in
  // place. Drop the cache whenever corpus-derived state changes so sync/status
  // checks never reuse a pre-edit hash.
  recordFingerprintCache=new WeakMap();
}
function allRows(){
  if(corpusCache.rows)return corpusCache.rows;
  const rows=[];
  for(const file of state.files){
    for(let index=0;index<file.records.length;index++)rows.push({file,record:file.records[index],index});
  }
  corpusCache.rows=rows;
  return rows;
}
function memoCorpus(key,builder){
  if(corpusCache.memo.has(key))return corpusCache.memo.get(key);
  const value=builder();
  corpusCache.memo.set(key,value);
  return value;
}
function hasChromaService(){return state.health?.chroma?.available===true}
function hasCorpusDb(){return hasChromaService()&&recordStores().length>0}
function dbUnavailableReason(){
  if(!hasChromaService())return "ChromaDB is unavailable. Start/connect ChromaDB before using database features.";
  if(!recordStores().length)return "Create or restore a corpus vector database first.";
  return "";
}
function isResearcher(){return Boolean(state.userContext&&state.userContext.role!=="admin")}
function hasCapability(capability){
  if(!state.userContext)return false;
  if(state.userContext.role==="admin")return true;
  const capabilities=new Set(state.userContext.capabilities||[]);
  return capabilities.has("*")||capabilities.has(capability);
}
function userCapabilities(){
  return {
    viewSharedPages:hasCapability("page.dashboard"),
    annotate:hasCapability("annotations.write"),
    compare:hasCapability("page.compare"),
    research:hasCapability("rag.run"),
    editLocalRecords:hasCapability("records.edit"),
    manageCorpus:hasCapability("corpus.manage"),
    manageUsers:hasCapability("users.manage"),
    configureProviders:hasCapability("providers.manage"),
  };
}
const pageCapabilities={home:"page.dashboard",list:"page.records",record:"page.record",works:"page.works",global:"page.search",annotations:"page.annotations",pdf:"page.pdf",compare:"page.compare",vector:"page.vector",rag:"page.research",faq:"page.faq",responsecache:"page.response_cache",providers:"page.providers",config:"page.settings"};
function canUse(feature){return Boolean(userCapabilities()[feature]);}
function canAccessPage(view){const capability=pageCapabilities[view];return !capability||hasCapability(capability);}
function setUserContext(user){
  const priorId=state.userContext?.id;
  state.userContext=user||null;
  if(priorId!==state.userContext?.id){state.serverAnnotations=[];state.serverAnnotationsStore="";state.annotationsFetchedAt=0}
  if(!canAccessPage(state.view))state.view="home";
  void refreshResearcherContentPolicy();
}
function viewDisabledReason(view){
  if(!canAccessPage(view))return "This workspace is available to administrators only.";
  if(view==="vector"&&isResearcher()&&!hasChromaService())return dbUnavailableReason();
  if(view==="faq"&&!hasChromaService())return "ChromaDB is unavailable, so the Response Library cannot be opened.";
  if(view==="responsecache"&&!hasChromaService())return "ChromaDB is unavailable, so the response cache cannot be opened.";
  return "";
}
/** @param {Document | Element} [root=document] */
function decorateDisabledControls(root=document){
  root.querySelectorAll?.("button:disabled,input:disabled,select:disabled").forEach(control=>{
    if(control.closest?.(".disabled-control-tooltip"))return;
    const explicit=control.dataset.disabledReason;
    const existingTitle=String(control.title||"").trim();
    const id=(control.id||"").toLowerCase();
    const text=String(control.textContent||"").trim().toLowerCase();
    const pageAction=String(control.dataset.page||"").split(":").at(-1);
    let reason=explicit||existingTitle||"This action is unavailable until its required selection or data is available.";
    if(!explicit&&!existingTitle&&(pageAction==="first"||pageAction==="prev"))reason="You are already on the first page.";
    else if(!explicit&&!existingTitle&&(pageAction==="next"||pageAction==="last"))reason="You are already on the last page.";
    else if(!explicit&&!existingTitle&&control.dataset.up!==undefined)reason="This column is already first.";
    else if(!explicit&&!existingTitle&&control.dataset.down!==undefined)reason="This column is already last.";
    else if(id==="breadcrumbback")reason="There is no earlier navigation location.";
    else if(id==="breadcrumbforward")reason="There is no forward navigation location.";
    else if(id==="loadraghistory")reason="Choose a previous RAG question first.";
    else if(id==="applyjobselected"||id==="applyselectedchanges")reason="Select at least one proposed change first.";
    else if(id==="nukeeverything")reason=tr("config.nuke.type_to_enable_help",'Type "NUKE" exactly to enable this destructive action.');
    else if(id==="linkpdf")reason="The current PDF page is already linked to this record.";
    else if(id==="runsearch")reason="Semantic search is unavailable for precomputed-only collections.";
    else if(["ragmodel","toolmodel","touchmodel"].includes(id))reason="The provider is configured to choose the model automatically.";
    else if(id==="columnadd")reason="Every available field is already shown.";
    else if(id==="importactive")reason="Load and select a JSONL tab first.";
    else if(id==="importall")reason="Load at least one JSONL tab first.";
    else if(["extractpage","extractall","pdfllmclean","pdfllmdraft"].includes(id))reason="Load a PDF page with extractable text first.";
    else if(["pdfllmlink","linkcurrentpdf"].includes(id))reason="Load JSONL records before linking a PDF page.";
    else if(["collectionembeddingprovider","collectionembeddingmodel","saveembeddingsettings"].includes(id))reason="Embedding settings are locked after a collection contains records; create a new empty collection to change them.";
    else if(id==="runtouchup")reason="Configure a reachable LLM provider and model before running this operation.";
    else if(text.includes("cancelling"))reason="Cancellation has already been requested for this operation.";
    else if(/upsert|sync|rag/.test(id))reason=dbUnavailableReason()||reason;
    else if(/prev|older/.test(id))reason="There is no previous item or older version.";
    else if(/next|newer/.test(id))reason="There is no next item or newer version.";
    else if(/merge/.test(id))reason="Load at least two JSONL tabs to merge them.";
    else if(/subset|bulk|export/.test(id))reason="Load JSONL records first.";
    else if(/edit/.test(id))reason="Select a record first.";
    if(explicit)reason=explicit;
    control.title=reason;
    if(control.tagName==="BUTTON"&&!control.closest(".disabled-control-tooltip")){
      const wrapper=document.createElement("span");wrapper.className="disabled-control-tooltip";wrapper.dataset.tooltip=reason;control.parentNode?.insertBefore(wrapper,control);wrapper.appendChild(control);
    }
  });
}
function showAppModal(dialog){
  decorateDisabledControls(dialog);
  dialog.showModal();
}

function workspaceDbName(){
  return isResearcher()&&state.userContext?.id?`${DB_NAME}-researcher-${state.userContext.id}`:DB_NAME;
}
let prefsTimer=null;
const fileTimers=new Map();
const {openMergeDialog,openSubsetBuilder,openBulkFieldEditor,openOcrCleanupDialog,openEditor,openStoreRecordEditor,openRecordHistoryBrowser,openUpsertQueue}=createRecordDialogs({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  activeFile:(...args)=>activeFile(...args),
  allRows:(...args)=>allRows(...args),
  api:(...args)=>api(...args),
  applyRecordChanges:(...args)=>applyRecordChanges(...args),
  bulkEditRowsForScope:(...args)=>bulkEditRowsForScope(...args),
  cleanRows:(...args)=>cleanRows(...args),
  clearRecordUpdates:(...args)=>clearRecordUpdates(...args),
  cloneAuditValue:(...args)=>cloneAuditValue(...args),
  dbUnavailableReason:(...args)=>dbUnavailableReason(...args),
  decorateDisabledControls:(...args)=>decorateDisabledControls(...args),
  download:(...args)=>download(...args),
  downloadBlob:(...args)=>downloadBlob(...args),
  fieldEditor:(...args)=>fieldEditor(...args),
  fileJsonl:(...args)=>fileJsonl(...args),
  fileTimers,
  formatTimestamp:(...args)=>formatTimestamp(...args),
  hasCorpusDb:(...args)=>hasCorpusDb(...args),
  historyVersionChanges:(...args)=>historyVersionChanges(...args),
  idbDelete:(...args)=>idbDelete(...args),
  jsonPretty:(...args)=>jsonPretty(...args),
  label:(...args)=>label(...args),
  loadSubsetProfiles:(...args)=>loadSubsetProfiles(...args),
  localRecordKey:(...args)=>localRecordKey(...args),
  navigateTo:(...args)=>navigateTo(...args),
  needsReviewItems:(...args)=>needsReviewItems(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  parseBulkFieldValue:(...args)=>parseBulkFieldValue(...args),
  parseEditor:(...args)=>parseEditor(...args),
  pendingChangesForRow:(...args)=>pendingChangesForRow(...args),
  pendingUpsertRows:(...args)=>pendingUpsertRows(...args),
  persistFileNow:(...args)=>persistFileNow(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  recordDbStatus:(...args)=>recordDbStatus(...args),
  recordFields:(...args)=>recordFields(...args),
  recordHistoryVersions:(...args)=>recordHistoryVersions(...args),
  refreshPresenceForRows:(...args)=>refreshPresenceForRows(...args),
  removeFromUpsertQueue:(...args)=>removeFromUpsertQueue(...args),
  renderView:(...args)=>renderView(...args),
  restoreRecordHistoryVersion:(...args)=>restoreRecordHistoryVersion(...args),
  sameValue:(...args)=>sameValue(...args),
  saveSubsetProfiles:(...args)=>saveSubsetProfiles(...args),
  selectedIndex:(...args)=>selectedIndex(...args),
  selectedRecord:(...args)=>selectedRecord(...args),
  selectedReviewItems:(...args)=>selectedReviewItems(...args),
  shell:(...args)=>shell(...args),
  showAppModal:(...args)=>showAppModal(...args),
  subsetRuleMatches:(...args)=>subsetRuleMatches(...args),
  toast:(...args)=>toast(...args),
  tr:(...args)=>tr(...args),
  trf:(...args)=>trf(...args),
  uid:(...args)=>uid(...args),
  upsertRows:(...args)=>upsertRows(...args),
});

const workspaceDb=createWorkspaceDb(workspaceDbName);
const idbGetAll=workspaceDb.getAll;
const idbGet=workspaceDb.get;
const idbPut=workspaceDb.put;
const idbDelete=workspaceDb.remove;
async function deleteWorkspaceDatabase(){
  clearTimeout(prefsTimer);
  for(const timer of fileTimers.values())clearTimeout(timer);
  fileTimers.clear();
  await workspaceDb.drop();
}
const deleteAllDerridaiBrowserState=()=>deleteAllDerridaiBrowserStateCompat(deleteWorkspaceDatabase);
async function persistCurrentPdfAsset(){
  if(!state.pdf.file)return;
  try{
    const blob=state.pdf.file instanceof Blob
      ? state.pdf.file
      : new Blob([await state.pdf.file.arrayBuffer()],{type:"application/pdf"});
    await idbPut("assets",{
      key:"current_pdf",
      blob,
      name:state.pdf.name||state.pdf.file.name||"current.pdf",
      title:state.pdf.title||"",
      author:state.pdf.author||"",
      page:state.pdf.page||1,
      rotation:state.pdf.rotation||0,
      text:state.pdf.text||"",
      search:state.pdf.search||"",
      relatedSearch:state.pdf.relatedSearch||"",
      extractionSource:state.pdf.extractionSource||"",
      extractError:state.pdf.extractError||"",
      saved_at:new Date().toISOString(),
    });
  }catch(error){
    console.warn("Could not persist current PDF asset",error);
  }
}
async function restoreCurrentPdfAsset(){
  try{
    const asset=await idbGet("assets","current_pdf");
    if(!asset?.blob)return;
    const file=new File([asset.blob],asset.name||"restored.pdf",{type:asset.blob.type||"application/pdf"});
    const buffer=await file.arrayBuffer();
    if(state.pdf.url)URL.revokeObjectURL(state.pdf.url);
    state.pdf.file=file;
    state.pdf.url=URL.createObjectURL(new Blob([buffer],{type:"application/pdf"}));
    state.pdf.name=file.name;
    state.pdf.title=asset.title||file.name.replace(/\.pdf$/i,"");
    state.pdf.author=asset.author||"";
    state.pdf.page=Math.max(1,Number(asset.page)||1);
    state.pdf.rotation=Number(asset.rotation||0)%360;
    state.pdf.text=String(asset.text||"");
    state.pdf.search=String(asset.search||"");
    state.pdf.relatedSearch=String(asset.relatedSearch||"");
    state.pdf.extractionSource=String(asset.extractionSource||"");
    state.pdf.extractError=String(asset.extractError||"");
    try{
      state.pdf.doc=await pdfjsLib.getDocument({data:new Uint8Array(buffer.slice(0))}).promise;
      const metadata=await loadPdfMetadata(state.pdf.doc,file.name);
      state.pdf.title=asset.title||metadata.title||state.pdf.title;
      state.pdf.author=asset.author||metadata.author||state.pdf.author;
      state.pdf.page=Math.min(state.pdf.page,state.pdf.doc.numPages||state.pdf.page);
    }catch(error){
      state.pdf.doc=null;
      state.pdf.extractError=`Restored PDF.js initialization failed (${error.message}).`;
    }
  }catch(error){
    console.warn("Could not restore current PDF asset",error);
  }
}

function serializableFile(file){
  return serializableRecordsFile(file);
}
async function persistFileNow(file){
  invalidateCorpusCache();
  try{
    await idbPut("files",serializableFile(file));
  }catch(error){
    console.error("IndexedDB file persistence failed",error);
    toast(`Local persistence failed: ${error.message}`);
  }
}
function persistFile(file){
  invalidateCorpusCache();
  clearTimeout(fileTimers.get(file.id));
  const timer=setTimeout(()=>{fileTimers.delete(file.id);persistFileNow(file)},250);
  fileTimers.set(file.id,timer);
}
function workspacePrefs(){
  return {
    key:"workspace",
    activeFileId:state.activeFileId,
    view:state.view,
    selected:state.selected,
    searches:state.searches,
    listFilters:state.listFilters,
    pages:state.pages,
    pageSize:state.pageSize,
    sorts:state.sorts,
    globalSearch:state.globalSearch,
    globalFilters:state.globalFilters,
    globalSort:state.globalSort,
    globalPage:state.globalPage,
    globalSearchMode:state.globalSearchMode,
    dbSearchMethod:state.dbSearchMethod,
    dbSearchWhere:state.dbSearchWhere,
    dbSearchFetchK:state.dbSearchFetchK,
    dbSearchLambda:state.dbSearchLambda,
    globalAdvancedOpen:state.globalAdvancedOpen,
    searchFacetFilters:state.searchFacetFilters,
    worksSearch:state.worksSearch,
    workOverview:state.workOverview,
    researcherRecordId:state.researcherRecordId,
    researcherCompareA:state.researcherCompareA,
    researcherCompareB:state.researcherCompareB,
    dashboardMetricIndex:state.dashboardMetricIndex,
    lastViewedRecord:state.lastViewedRecord,
    compareA:state.compareA,
    compareB:state.compareB,
    compareMode:state.compareMode,
    comparePasteA:state.comparePasteA,
    comparePasteB:state.comparePasteB,
    compareSourceA:state.compareSourceA,
    compareSourceB:state.compareSourceB,
    compareFilter:state.compareFilter,
    activeStore:state.activeStore,
    storePage:state.storePage,
    storePageSize:state.storePageSize,
    storeQuery:state.storeQuery,
    storeSearchMode:state.storeSearchMode,
    storeWork:state.storeWork,
    storeSort:state.storeSort,
    storeFilters:state.storeFilters,
    storeBrowseMode:state.storeBrowseMode,
    vectorTab:state.vectorTab,
    vectorCollectionFilter:state.vectorCollectionFilter,
    llmConfig:state.llmConfig,
    appConfig:state.appConfig,
    ragConfig:state.ragConfig,
    faqSearch:state.faqSearch,
    faqPage:state.faqPage,
    faqExpanded:state.faqExpanded,
    navHistory:state.navHistory,
    navForward:state.navForward,
    sidebarCollapsed:state.sidebarCollapsed,
    collectionsCollapsed:state.collectionsCollapsed,
    operationToastsMinimized:state.operationToastsMinimized,
    operationStackPosition:state.operationStackPosition,
    collapsedPanels:state.collapsedPanels,
    tableColumns:state.tableColumns,
    upsertState:state.upsertState,
    upsertIgnored:state.upsertIgnored,
    jobApplied:state.jobApplied,
    upsertJobApplied:state.upsertJobApplied,
    reviewSelection:[...state.reviewSelection],
    selectedEvidence:state.selectedEvidence,
    storeSearchSort:state.storeSearchSort,
  };
}
function persistPrefs(){
  if(!state.storageReady)return;
  clearTimeout(prefsTimer);
  prefsTimer=setTimeout(()=>idbPut("prefs",workspacePrefs()).catch(error=>console.error("IndexedDB preference persistence failed",error)),400);
}
async function flushWorkspacePrefs(){
  if(!state.storageReady)throw new Error("Workspace storage is not ready yet.");
  clearTimeout(prefsTimer);
  await idbPut("prefs",workspacePrefs());
}
async function restoreWorkspace(){
  try{
    const [savedFiles,prefs]=await Promise.all([idbGetAll("files"),idbGet("prefs","workspace")]);
    state.files=(savedFiles||[]).map(file=>({
      ...file,
      dirty:new Set(file.dirty||[]),
      errors:file.errors||[],
    }));
    // getShellSnapshot/workIndex can be queried before IndexedDB restore finishes.
    // Always drop derived corpus indexes after reattaching persisted files so the
    // Works page and corpus metrics cannot remain stuck on a cached empty corpus.
    invalidateCorpusCache();
    if(prefs){
      const preservedAppDefaults={...state.appConfig};
      const preservedLlmDefaults={...state.llmConfig};
      for(const key of ["selected","searches","listFilters","pages","sorts","globalSearch","globalFilters","globalSort","globalPage","globalSearchMode","globalSearchAutoRun","searchResultLayouts","dbSearchMethod","dbSearchWhere","dbSearchFetchK","dbSearchLambda","globalAdvancedOpen","searchFacetFilters","worksSearch","workOverview","researcherRecordId","researcherCompareA","researcherCompareB","dashboardMetricIndex","lastViewedRecord","compareA","compareB","compareMode","comparePasteA","comparePasteB","compareSourceA","compareSourceB","compareFilter","faqSearch","faqPage","faqExpanded","activeStore","storePage","storePageSize","storeQuery","storeSearchMode","storeWork","storeSort","storeFilters","storeBrowseMode","vectorTab","vectorCollectionFilter","storeSearchSort","selectedEvidence","navHistory","navForward","sidebarCollapsed","collectionsCollapsed","operationToastsMinimized","operationStackPosition","collapsedPanels","tableColumns","upsertState","upsertIgnored","jobApplied","upsertJobApplied"]){
        if(prefs[key]!==undefined)state[key]=prefs[key];
      }
      state.appConfig={...preservedAppDefaults,...(prefs.appConfig||{})};
      applyUiTheme(state.appConfig.ui_color_theme);
      state.llmConfig={...preservedLlmDefaults,...(prefs.llmConfig||{})};
      state.ragConfig={...state.ragConfig,...(prefs.ragConfig||{})};
      if(!state.faqExpanded||typeof state.faqExpanded!=="object"||Array.isArray(state.faqExpanded))state.faqExpanded={};
      state.ragConfig.locales=Array.isArray(state.ragConfig.locales)?state.ragConfig.locales.filter(value=>value==="en"||value==="fr"):["en","fr"];
      if(!state.ragConfig.locales.length)state.ragConfig.locales=["en","fr"];
      state.ragConfig.prompt=String(state.ragConfig.prompt||"");
      state.ragConfig.instructions=String(state.ragConfig.instructions||"");
      if(!Array.isArray(state.ragConfig.history))state.ragConfig.history=[];
      state.ragConfig.history=state.ragConfig.history.slice(0,100);
      if(!Array.isArray(state.ragConfig.run_history))state.ragConfig.run_history=[];
      state.ragConfig.run_history=state.ragConfig.run_history.slice(0,250);
      if(!state.appConfig.default_review_preset)state.appConfig.default_review_preset="text";
      if(!state.appConfig.default_llm_run_mode)state.appConfig.default_llm_run_mode="foreground";
      ensureProviderProfiles();
      if(Number.isFinite(+prefs.pageSize))state.pageSize=+prefs.pageSize;
      if(typeof prefs.view==="string")state.view=prefs.view;
      state.reviewSelection=new Set(prefs.reviewSelection||[]);
      state.activeFileId=state.files.some(f=>f.id===prefs.activeFileId)?prefs.activeFileId:(state.files[0]?.id||null);
    }else{
      // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
      state.activeFileId=state.files[0]?.id||null;ensureProviderProfiles();try{state.appConfig.ui_color_theme=localStorage.getItem("derridai.ui.theme")||state.appConfig.ui_color_theme||"green"}catch{}applyUiTheme(state.appConfig.ui_color_theme);
    }
    const validPrefixes=new Set(state.files.map(f=>f.id));
    state.reviewSelection=new Set([...state.reviewSelection].filter(key=>validPrefixes.has(String(key).split("::")[0])));
    await restoreCurrentPdfAsset();
  }catch(error){
    console.error("Could not restore IndexedDB workspace",error);
    toast(`Could not restore saved workspace: ${error.message}`);
  }finally{
    state.storageReady=true;
  }
}
function reviewKey(file,index){return `${file.id}::${index}`}
function reviewItemFromKey(key){
  const split=String(key).lastIndexOf("::");
  if(split<0)return null;
  const fileId=key.slice(0,split),index=Number(key.slice(split+2));
  const file=state.files.find(f=>f.id===fileId);
  if(!file||!Number.isInteger(index)||!file.records[index])return null;
  return {file,index,record:file.records[index],key};
}
function selectedReviewItems(){return [...state.reviewSelection].map(reviewItemFromKey).filter(Boolean)}

async function copyCitation(record,kind="inline"){
  const text=kind==="full"?fullCitation(record):inlineCitation(record);
  try{await navigator.clipboard.writeText(text);toast(`Copied ${kind} citation`,{tone:"success"})}
  catch(error){toast(`Could not copy citation: ${error.message}`,{tone:"danger"})}
}
function workspaceEvidenceKey(file,index){return `workspace:${file.id}:${index}`}
function dbEvidenceKey(collection,id){return `db:${collection}:${id}`}
function selectedEvidenceEntries(){return Object.values(state.selectedEvidence||{}).filter(Boolean)}
function evidenceIsSelected(key){return Boolean(state.selectedEvidence?.[key])}
function setEvidence(key,item,selected=true){
  if(!state.selectedEvidence||typeof state.selectedEvidence!=="object")state.selectedEvidence={};
  if(selected)state.selectedEvidence[key]=item;else delete state.selectedEvidence[key];
  persistPrefs();
  shellRefreshHook();
}
function workspaceDbEvidenceTarget(file,index,record=file?.records?.[index]){
  if(!record||!state.activeStore)return null;
  const status=recordDbStatus(file,index,record);
  if(!["synced","exists"].includes(status.kind))return null;
  const receipt=storeReceipt(state.activeStore,file,index);
  const key=localRecordKey(file,index);
  const confirmedId=state.storePresenceIds?.[state.activeStore]?.[key];
  const id=String(receipt?.chroma_id||confirmedId||record.record_id||"").trim();
  return id?{collection:state.activeStore,id,key:dbEvidenceKey(state.activeStore,id)}:null;
}
function workspaceEvidenceSelectionKey(file,index){
  const local=workspaceEvidenceKey(file,index);
  if(evidenceIsSelected(local))return local;
  return workspaceDbEvidenceTarget(file,index)?.key||local;
}
function toggleWorkspaceEvidence(file,index){
  if(!hasCapability("evidence.select")){toast(tr("permissions.evidence_denied","Your role cannot change selected evidence."),{tone:"warn"});return}
  const record=file?.records?.[index];if(!record)return;
  const localKey=workspaceEvidenceKey(file,index);
  if(evidenceIsSelected(localKey)){setEvidence(localKey,null,false);return}
  const dbTarget=workspaceDbEvidenceTarget(file,index,record);
  if(dbTarget){toggleDbEvidence(dbTarget.collection,dbTarget.id,record);return}
  setEvidence(localKey,{
    key:localKey,kind:"workspace",file_id:file.id,index,record_id:record.record_id||"",work:record.work||"",
    page_start:record.page_start??record.page??null,page_end:record.page_end??null,
    speaker:record.speaker||null,position_holder:record.position_holder||null,stance:record.stance||null,
    discourse_role:record.discourse_role||null,target:record.target||null,proposition_status:record.proposition_status||null,
    inline_citation:record.inline_citation||null,text_preview:String(record.text||"").replace(/\s+/g," ").trim().slice(0,280),
    label:`${record.record_id||`Record ${index+1}`} · ${record.work||file.name}`
  },true);
}
function toggleDbEvidence(collection,id,record={}){
  if(!hasCapability("evidence.select")){toast(tr("permissions.evidence_denied","Your role cannot change selected evidence."),{tone:"warn"});return}
  if(!collection||!id)return;
  const key=dbEvidenceKey(collection,id);
  setEvidence(key,{
    key,kind:"db",collection,chroma_id:id,record_id:record.record_id||id,work:record.work||"",
    page_start:record.page_start??record.page??null,page_end:record.page_end??null,
    speaker:record.speaker||null,position_holder:record.position_holder||null,stance:record.stance||null,
    discourse_role:record.discourse_role||null,target:record.target||null,proposition_status:record.proposition_status||null,
    inline_citation:record.inline_citation||null,text_preview:String(record.text||"").replace(/\s+/g," ").trim().slice(0,280),
    label:`${record.record_id||id} · ${record.work||collection}`
  },!evidenceIsSelected(key));
}
function clearSelectedEvidence(){
  if(!hasCapability("evidence.select")){toast(tr("permissions.evidence_denied","Your role cannot change selected evidence."),{tone:"warn"});return}
  state.selectedEvidence={};persistPrefs();shellRefreshHook()
}
function selectedEvidencePayload(){
  const payload=[];
  for(const item of selectedEvidenceEntries()){
    if(item.kind==="db")payload.push({collection:item.collection,chroma_id:item.chroma_id});
    else if(item.kind==="workspace"){
      const file=state.files.find(file=>file.id===item.file_id);
      const record=file?.records?.[Number(item.index)];
      if(record)payload.push({record:ragEvidenceRecordPayload(record)});
    }
  }
  return payload;
}
function setReviewSelected(file,index,selected){
  const key=reviewKey(file,index);
  selected?state.reviewSelection.add(key):state.reviewSelection.delete(key);
  persistPrefs();
}
function clearReviewSelection(){
  state.reviewSelection.clear();
  persistPrefs();
}

// 0.30.11 packet discipline: API boundaries receive only fields required by
// the operation. Audit history is intentionally opt-in because it can dwarf
// the rest of a record after repeated edits.
const TOUCHUP_TRANSPORT_CONTEXT_FIELDS=[
  "record_id","work","document_author","edition","year","page_start","page_end",
  "region_type","region_author","primary_text","speaker","position_holder","target",
  "discourse_role","proposition_status","semantic_function","stance","claim_scope",
  "text","topics","concepts","persons","works_referenced","is_direct_quote",
  "quoted_speaker","quoted_author","quoted_work","quoted_position_holder",
  "quoted_addressee","quoted_referent","quotation_chain","inline_citation",
  "full_citation","needs_review","review_reason"
];
const RAG_EVIDENCE_TRANSPORT_FIELDS=[
  "record_id","canonical_work_id","work","document_author","edition","year",
  "page_start","page_end","translator","speaker","position_holder","target",
  "discourse_role","proposition_status","stance","text","topics","concepts",
  "persons","document_language","document_languages","quoted_speaker",
  "quoted_author","quoted_work","quoted_position_holder"
];
function upsertRecordPayload(record,chromaId=null){
  const out=recordPayload(record,{includeChromaId:false});
  if(chromaId)out._chroma_id=chromaId;
  return out;
}
function touchupRecordPayload(record,fields=[]){
  return recordPayload(record,{fields:[...fields,...TOUCHUP_TRANSPORT_CONTEXT_FIELDS]});
}
function ragEvidenceRecordPayload(record){
  return recordPayload(record,{fields:RAG_EVIDENCE_TRANSPORT_FIELDS});
}
function applyRecordChanges(file,index,changes,{source="manual",model=null,batchId=null,rationale=null}={}){
  const current=file.records[index];
  if(!current)return 0;
  const pending={};
  for(const [field,newValue] of Object.entries(changes||{})){
    if(field==="updates")continue;
    if(!sameValue(current[field],newValue))pending[field]=newValue;
  }
  if("text" in pending && "text_length" in current && !("text_length" in pending)){
    const length=String(pending.text??"").length;
    if(!sameValue(current.text_length,length))pending.text_length=length;
  }
  const entries=Object.entries(pending);
  if(!entries.length)return 0;
  const timestamp=new Date().toISOString();
  const operationId=batchId||uid();
  const history=Array.isArray(current.updates)?current.updates.map(cloneAuditValue):[];
  const next={...current};
  for(const [field,newValue] of entries){
    const entry={
      field_name:field,
      old_value:cloneAuditValue(current[field]),
      new_value:cloneAuditValue(newValue),
      timestamp,
      source,
      batch_id:operationId,
      initiated_by:state.userContext?.username||null,
    };
    if(model)entry.model=model;
    if(rationale?.[field])entry.reason=String(rationale[field]);
    history.push(entry);
    next[field]=newValue;
  }
  next.updates=history;
  file.records[index]=next;
  file.dirty.add(index);
  invalidateCorpusCache();
  persistFile(file);
  if(state.view==="record"&&typeof window!=="undefined")window.dispatchEvent(new CustomEvent("derridai:record-updated"));
  return entries.length;
}

async function clearRecordUpdates(file,index,{confirmFirst=true}={}){
  const record=file?.records?.[index];
  const count=Array.isArray(record?.updates)?record.updates.length:0;
  if(!record||!count){
    toast("This record has no updates history");
    return false;
  }
  if(confirmFirst&&!await openMessageModal({title:"Clear record update history?",message:`Clear all ${count} updates entries from ${record.record_id||`record ${index+1}`}? This history cannot be reconstructed automatically.`,tone:"danger",confirmLabel:"Clear history",cancelLabel:"Cancel"}))return false;
  file.records[index]={...record,updates:[]};
  file.dirty.add(index);
  persistFile(file);
  return true;
}
async function clearAllUpdates({confirmed=false}={}){
  const rows=allRows().filter(row=>Array.isArray(row.record.updates)&&row.record.updates.length);
  if(!rows.length)return toast("No loaded records have updates history");
  const entries=rows.reduce((sum,row)=>sum+row.record.updates.length,0);
  if(!confirmed&&!await openMessageModal({title:"Clear all update histories?",message:`Clear ${entries.toLocaleString()} updates entries from ${rows.length.toLocaleString()} loaded records? This permanently removes the local audit histories.`,tone:"danger",confirmLabel:"Clear all histories",cancelLabel:"Cancel"}))return;
  const files=new Set();
  for(const row of rows){
    row.file.records[row.index]={...row.record,updates:[]};
    row.file.dirty.add(row.index);
    files.add(row.file);
  }
  for(const file of files)persistFile(file);
  shell();renderView();
  toast(`Cleared updates history from ${rows.length.toLocaleString()} records`);
}

function formatTimestamp(value){
  if(!value)return "";
  const date=new Date(value);
  return Number.isNaN(date.getTime())?String(value):date.toLocaleString();
}
function historyVersionChanges(previous,current){
  const keys=new Set([...Object.keys(previous||{}),...Object.keys(current||{})]);
  return [...keys].filter(key=>key!=="updates"&&!key.startsWith("_")&&!sameValue(previous?.[key],current?.[key])).sort((a,b)=>label(a).localeCompare(label(b)));
}
function restoreRecordHistoryVersion(file,index,version){
  const current=file?.records?.[index];
  if(!current||!version?.record)return 0;
  const keys=new Set([...Object.keys(current),...Object.keys(version.record)]);
  const changes={};
  for(const field of keys){
    if(field==="updates"||field.startsWith("_"))continue;
    const value=Object.prototype.hasOwnProperty.call(version.record,field)?cloneAuditValue(version.record[field]):null;
    if(!sameValue(current[field],value))changes[field]=value;
  }
  return applyRecordChanges(file,index,changes,{source:"history_restore",batchId:uid(),rationale:Object.fromEntries(Object.keys(changes).map(field=>[field,`Restored from ${version.label}`]))});
}


function openMessageModal({
  title="Notice",
  message="",
  detail="",
  tone="info",
  confirmLabel="OK",
  cancelLabel=null,
}={}){
  return new Promise(resolve=>{
    const dialog=document.createElement("dialog");
    dialog.className=`message-dialog ${tone}`;
    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2>${detail?`<div class="dialog-subtitle">${esc(detail)}</div>`:""}</div><button class="btn icon-only" data-cancel>${icon("close")}</button></div><div class="db"><div class="message-modal-body">${esc(message).replace(/\n/g,"<br>")}</div></div><div class="da">${cancelLabel?`<button class="btn" data-cancel>${esc(cancelLabel)}</button>`:""}<button class="btn ${tone==="danger"?"danger":"primary"}" data-confirm>${esc(confirmLabel)}</button></div>`;
    document.body.appendChild(dialog);
    const finish=value=>{dialog.close();dialog.remove();resolve(value)};
    dialog.querySelectorAll("[data-cancel]").forEach(button=>button.onclick=()=>finish(false));
    dialog.querySelector("[data-confirm]").onclick=()=>finish(true);
    dialog.addEventListener("cancel",event=>{event.preventDefault();finish(false)},{once:true});
    showAppModal(dialog);
  });
}
async function copyJsonToClipboard(value,labelText="record"){
  const text=JSON.stringify(value,null,2);
  try{
    await navigator.clipboard.writeText(text);
    toast(`Copied ${labelText} JSON`);
  }catch(error){
    const area=document.createElement("textarea");
    area.value=text;
    area.style.position="fixed";
    area.style.opacity="0";
    document.body.appendChild(area);
    area.select();
    try{document.execCommand("copy");toast(`Copied ${labelText} JSON`)}
    catch{openMessageModal({title:"Could not copy",message:error.message,tone:"danger"})}
    finally{area.remove()}
  }
}
function isResponseCacheStore(store){
  return Boolean(store&&(store.name==="_response_cache"||store.storage_name==="derridai_response_cache"||store.metadata?.derridai_system_collection==="response_cache"));
}
function recordStores(){
  return state.stores.filter(store=>!isResponseCacheStore(store));
}
function responseCacheStore(){
  return state.stores.find(isResponseCacheStore)||null;
}
function corpusStoreExists(name){
  return Boolean(name&&recordStores().some(store=>store.name===name));
}





let progressiveRenderToken=0;
function loadingCardsHtml(label="Loading",count=4){
  return `<div class="progressive-loading" role="status" aria-live="polite"><div class="progressive-loading-head"><span class="spinner small-spinner"></span><b>${esc(label)}</b></div><div class="progressive-skeleton-grid">${Array.from({length:count},()=>'<div class="progressive-skeleton-card"><i></i><i></i><i></i></div>').join("")}</div></div>`;
}
function showViewLoading(main,title="Loading view",detail="Preparing data…"){
  if(!main)return;
  main.innerHTML=`<section class="card view-loading-card"><div class="view-loading-copy"><span class="spinner"></span><div><b>${esc(title)}</b><p>${esc(detail)}</p></div></div>${loadingCardsHtml("Loading cards",3)}</section>`;
}

function pages(r){
  if(r.page_start==null && r.page_end==null) return "—";
  return r.page_end!=null && r.page_end!==r.page_start ? `${display(r.page_start)}–${display(r.page_end)}` : display(r.page_start);
}

function toggleSort(sort,key){if(sort.key===key)sort.dir*=-1;else{sort.key=key;sort.dir=1}}

function pageInfo(total,page){
  const pages=Math.max(1,Math.ceil(total/state.pageSize));
  page=Math.max(1,Math.min(pages,page||1));
  return {page,pages,start:(page-1)*state.pageSize,end:Math.min(total,page*state.pageSize)};
}

function recordFingerprint(record){
  if(record&&typeof record==="object"&&recordFingerprintCache.has(record))return recordFingerprintCache.get(record);
  const value=computeRecordFingerprint(record);
  if(record&&typeof record==="object")recordFingerprintCache.set(record,value);
  return value;
}
function localRecordKey(file,index){return `${file.id}::${index}`}
function storeReceipt(store,file,index){return state.upsertState?.[store]?.[localRecordKey(file,index)]||null}
function candidateChromaIds(file,index,record){
  const ids=[];
  const receipt=storeReceipt(state.activeStore,file,index);
  if(receipt?.chroma_id)ids.push(receipt.chroma_id);
  const logical=record?.record_id;
  if(logical!=null&&String(logical)!==""){
    ids.push(String(logical));
    ids.push(`${file.name}::${logical}`);
  }
  return [...new Set(ids)];
}
function recordDbStatus(file,index,record,store=state.activeStore){
  if(!hasCorpusDb())return {kind:"none",label:"No database",title:dbUnavailableReason()};
  if(!store)return {kind:"none",label:"No collection",title:"Select a Chroma collection"};
  if(!corpusStoreExists(store))return {kind:"none",label:"No collection",title:"The selected collection no longer exists"};
  const key=localRecordKey(file,index);
  const receipt=state.upsertState?.[store]?.[key]||null;
  const presence=state.storePresence?.[store]?.[key];
  const fingerprint=recordFingerprint(record);
  if(receipt&&receipt.fingerprint===fingerprint&&presence!==false)return {kind:"synced",label:"Synced",title:`Upserted ${formatTimestamp(receipt.timestamp)}`};
  if(receipt&&receipt.fingerprint!==fingerprint)return {kind:"changed",label:"Pending",title:"Changed since last upsert"};
  if(presence===true)return {kind:"exists",label:"In DB",title:"Record exists in the selected collection; local sync time is unknown"};
  if(presence===false)return {kind:"absent",label:"Not in DB",title:"Record was not found in the selected collection"};
  return {kind:"unknown",label:"Unknown",title:"Database presence has not been checked yet"};
}
function workDbStatus(rows,workName=null){
  if(!hasCorpusDb())return {kind:"none",label:"No database"};
  if(!state.activeStore)return {kind:"none",label:"No collection"};
  if(!corpusStoreExists(state.activeStore))return {kind:"none",label:"No collection"};
  const receipts=rows.map(row=>state.upsertState?.[state.activeStore]?.[localRecordKey(row.file,row.index)]||null);
  if(rows.some((row,index)=>receipts[index]&&receipts[index].fingerprint!==recordFingerprint(row.record)))return {kind:"changed",label:"Pending changes"};
  if(rows.length&&rows.every((row,index)=>receipts[index]?.fingerprint===recordFingerprint(row.record)))return {kind:"synced",label:"Synced"};
  if(state.storeWorksStore===state.activeStore){
    const name=workName??String(rows[0]?.record?.work||"(Untitled work)");
    const stat=(state.storeWorkStats||[]).find(item=>String(item.work||"(Untitled work)")===String(name));
    const dbCount=Number(stat?.count||0);
    if(dbCount>=rows.length&&rows.length)return {kind:"exists",label:"In DB"};
    if(dbCount>0)return {kind:"exists",label:`Partly in DB (${dbCount}/${rows.length})`};
    return {kind:"absent",label:"Not in DB"};
  }
  return {kind:"unknown",label:"DB status loading"};
}
async function refreshPresenceForRows(rows,{force=false}={}){
  const store=state.activeStore;
  if(!hasCorpusDb()||!store||!rows.length)return;
  if(!state.storePresence[store])state.storePresence[store]={};
  if(!state.storePresenceIds[store])state.storePresenceIds[store]={};
  if(!state.storePresenceCheckedAt[store])state.storePresenceCheckedAt[store]={};
  const now=Date.now(),ttl=15000;
  const staleRows=force?rows:rows.filter(row=>now-Number(state.storePresenceCheckedAt[store][localRecordKey(row.file,row.index)]||0)>ttl);
  if(!staleRows.length)return;
  const ids=[...new Set(staleRows.flatMap(row=>candidateChromaIds(row.file,row.index,row.record)))];
  if(!ids.length)return;
  const found=new Set();
  try{
    for(let start=0;start<ids.length;start+=500){
      const data=await api(`/api/stores/${encodeURIComponent(store)}/records/status`,{
        method:"POST",
        body:JSON.stringify({ids:ids.slice(start,start+500)}),
      });
      for(const id of data.existing_ids||[])found.add(id);
    }
    for(const row of staleRows){
      const key=localRecordKey(row.file,row.index);
      const candidates=candidateChromaIds(row.file,row.index,row.record);
      const matchedId=candidates.find(id=>found.has(id))||"";
      state.storePresence[store][key]=Boolean(matchedId);
      state.storePresenceIds[store][key]=matchedId;
      state.storePresenceCheckedAt[store][key]=now;
    }
    pendingUpsertCache.key="";
    updateDbStatusElements();
  }catch(error){
    console.warn("Could not refresh Chroma presence",error);
  }
}
function updateDbStatusElements(){
  document.querySelectorAll("[data-db-status-key]").forEach(el=>{
    const item=reviewItemFromKey(el.dataset.dbStatusKey);
    if(!item)return;
    const info=recordDbStatus(item.file,item.index,item.file.records[item.index]);
    el.className=`db-status ${info.kind}`;
    el.title=info.title;
    el.innerHTML=`<i></i>${esc(info.label)}`;
  });
  document.querySelectorAll("[data-work-status]").forEach(el=>{
    const work=el.dataset.workStatus;
    const rows=workIndex().get(work)?.rows||[];
    const info=workDbStatus(rows,work);
    el.className=`db-status ${info.kind}`;
    el.innerHTML=`<i></i>${esc(info.label)}`;
  });
}
function ignoredFingerprint(store,file,index){
  return state.upsertIgnored?.[store]?.[localRecordKey(file,index)]||null;
}
let pendingUpsertCache={key:"",at:0,rows:[]};
function pendingUpsertRows(){
  if(!hasCorpusDb()||!state.activeStore)return [];
  const dirtyCount=state.files.reduce((sum,file)=>sum+(file.dirty?.size||0),0);
  const key=`${state.activeStore}|${corpusCache.version}|${dirtyCount}|${Number(state.upsertJobApplied?Object.values(state.upsertJobApplied).reduce((a,b)=>a+Number(b||0),0):0)}`;
  const now=performance.now();
  if(pendingUpsertCache.key===key&&now-pendingUpsertCache.at<750)return pendingUpsertCache.rows;
  const rows=allRows().filter(row=>{
    const fingerprint=recordFingerprint(row.record);
    if(ignoredFingerprint(state.activeStore,row.file,row.index)===fingerprint)return false;
    const info=recordDbStatus(row.file,row.index,row.record);
    return info.kind==="changed" || info.kind==="absent" || (row.file.dirty.has(row.index)&&info.kind!=="synced");
  });
  pendingUpsertCache={key,at:now,rows};
  return rows;
}
function pendingChangesForRow(row){
  const store=state.activeStore;
  const receipt=storeReceipt(store,row.file,row.index);
  const since=receipt?.timestamp?new Date(receipt.timestamp).getTime():0;
  const updates=Array.isArray(row.record.updates)?row.record.updates:[];
  const changed=updates.filter(update=>{
    const time=new Date(update.timestamp||0).getTime();
    return !since || Number.isNaN(time) || time>since;
  });
  if(changed.length)return changed;
  if(!receipt)return [{
    field_name:"record",
    old_value:null,
    new_value:"Not previously upserted from this workspace",
    source:"workspace",
    timestamp:null,
  }];
  return [{
    field_name:"record",
    old_value:"Last upserted fingerprint",
    new_value:"Current record differs",
    source:"fingerprint",
    timestamp:null,
  }];
}
function removeFromUpsertQueue(row){
  const store=state.activeStore;
  if(!store)return;
  if(!state.upsertIgnored[store])state.upsertIgnored[store]={};
  state.upsertIgnored[store][localRecordKey(row.file,row.index)]=recordFingerprint(row.record);
  persistPrefs();
}
function recordFields(){
  if(corpusCache.fields)return corpusCache.fields;
  const set=new Set();
  allRows().forEach(x=>Object.keys(x.record).forEach(k=>set.add(k)));
  corpusCache.fields=[...set].sort();
  return corpusCache.fields;
}
function tableAvailableFields(rows,extra=[]){
  const cachedRows=allRows();
  if(rows===cachedRows){
    const set=new Set([...extra,...recordFields().filter(key=>key!=="updates")]);
    return [...set].sort((a,b)=>label(a).localeCompare(label(b)));
  }
  const set=new Set(extra);
  for(const row of rows)for(const key of Object.keys(row.record||row||{}))if(key!=="updates")set.add(key);
  return [...set].sort((a,b)=>label(a).localeCompare(label(b)));
}
function getTableColumns(table,available){
  const defaults=TABLE_DEFAULTS[table]||available.slice(0,8);
  let cols=Array.isArray(state.tableColumns[table])?state.tableColumns[table].filter(key=>available.includes(key)):[];
  if(!cols.length)cols=defaults.filter(key=>available.includes(key));
  if(!cols.length)cols=available.slice(0,8);
  state.tableColumns[table]=cols;
  return cols;
}

function setListFilterValue(fileId,key,value){
  if(!state.listFilters[fileId])state.listFilters[fileId]={};
  if(value===""||value==null)delete state.listFilters[fileId][key];
  else state.listFilters[fileId][key]=value;
  persistPrefs();
}


function pdfDisplayTitle(){
  return state.pdf.title||state.pdf.name||"PDF";
}
function loadedPdfPagesForRecord(record){
  if(!state.pdf.name)return [];
  return pdfLinks(record)
    .filter(link=>link.pdf_file===state.pdf.name)
    .map(link=>Number(link.pdf_page))
    .filter(page=>Number.isFinite(page)&&page>0)
    .sort((a,b)=>a-b);
}
function allLinkedRowsForLoadedPdf(){
  if(!state.pdf.name)return [];
  const rows=[];
  for(const {file,record,index} of allRows()){
    const pages=loadedPdfPagesForRecord(record);
    if(pages.length)rows.push({file,record,index,pages});
  }
  return rows.sort((a,b)=>
    (a.pages[0]||0)-(b.pages[0]||0)
    ||String(a.record.work||"").localeCompare(String(b.record.work||""))
    ||String(a.record.record_id||"").localeCompare(String(b.record.record_id||""))
  );
}
async function loadPdfMetadata(doc,fileName){
  const fallback=String(fileName||"").replace(/\.pdf$/i,"");
  if(!doc)return {title:fallback,author:""};
  try{
    const metadata=await doc.getMetadata();
    const info=metadata?.info||{};
    const xmp=metadata?.metadata;
    const title=String(
      info.Title
      ||xmp?.get?.("dc:title")
      ||xmp?.get?.("pdf:title")
      ||fallback
      ||""
    ).trim();
    const author=String(
      info.Author
      ||xmp?.get?.("dc:creator")
      ||xmp?.get?.("pdf:author")
      ||""
    ).trim();
    return {title:title||fallback,author};
  }catch(error){
    console.warn("Could not read PDF metadata",error);
    return {title:fallback,author:""};
  }
}
function openPdfExplorerWorkspace(){
  window.dispatchEvent(new CustomEvent("derridai:navigate-native",{detail:{path:"/pdf?mode=explorer",runtimeView:"pdf"}}));
}
function openLoadedPdfPage(page){
  if(!state.pdf.doc&& !state.pdf.file)return toast("Open the linked PDF in PDF Explorer first");
  const max=state.pdf.doc?.numPages||Number(page)||1;
  state.pdf.page=Math.max(1,Math.min(max,Number(page)||1));
  state.pdf.text="";
  state.pdf.extractError="";
  state.pdf.extractionSource="";
  openPdfExplorerWorkspace();
}

function needsReviewItems(rows=null){
  if(rows===null){
    return memoCorpus("needs-review-items",()=>allRows().filter(row=>row.record.needs_review===true).map(row=>({...row,key:reviewKey(row.file,row.index)})));
  }
  return rows.filter(row=>row.record.needs_review===true).map(row=>({...row,key:reviewKey(row.file,row.index)}));
}

function setActiveStore(name){
  const next=name||"";
  if(state.activeStore!==next){
    state.storeWorksStore="";
    // Presence maps can become very large for corpus-scale workspaces. Keep
    // only the selected store's map when switching collections.
    state.storePresence=next&&state.storePresence?.[next]?{[next]:state.storePresence[next]}:{};
    state.storePresenceIds=next&&state.storePresenceIds?.[next]?{[next]:state.storePresenceIds[next]}:{};
    state.storePresenceCheckedAt=next&&state.storePresenceCheckedAt?.[next]?{[next]:state.storePresenceCheckedAt[next]}:{};
  }
  state.activeStore=next;
  persistPrefs();
  syncUrl({replace:true});
}

async function buildUpsertItems(rows,store,{yieldEvery=0}={}){
  const idCounts=new Map();
  for(let i=0;i<rows.length;i++){const row=rows[i],id=String(row.file.records[row.index]?.record_id??"");idCounts.set(id,(idCounts.get(id)||0)+1);if(yieldEvery&&i&&i%yieldEvery===0)await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)))}
  const items=[];
  for(let i=0;i<rows.length;i++){
    const row=rows[i],current=row.file.records[row.index],logical=String(current?.record_id??""),receipt=storeReceipt(store,row.file,row.index),chromaId=receipt?.chroma_id||((idCounts.get(logical)||0)>1?`${row.file.name}::${logical}`:logical);
    const key=localRecordKey(row.file,row.index);
    const audit=upsertAuditDelta(current,receipt,state.storePresence?.[store]?.[key]);
    items.push({key,record:current,fingerprint:recordFingerprint(current),chroma_id:chromaId,file_name:row.file.name,...audit});
    if(yieldEvery&&i&&i%yieldEvery===0)await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));
  }
  return items;
}
async function upsertRows(rows,labelText="records",{largeSyncConfirmed=false}={}){
  if(!hasCorpusDb())return openMessageModal({title:"Vector database required",message:dbUnavailableReason(),confirmLabel:"OK"});
  if(!state.activeStore)return toast("Select a Chroma collection first");
  if(!rows.length)return toast("No records selected for upsert");
  const activeUpsert=state.jobs.find(job=>job.type==="upsert"&&["queued","running","cancelling"].includes(job.status));
  if(activeUpsert)return openMessageModal({title:tr("operations.vector_sync_active_title","A vector sync is already active"),message:trf("operations.vector_sync_active_help","{label} must finish or be cancelled before another collection build starts.",{label:activeUpsert.label||activeUpsert.store_name||"The current sync"}),confirmLabel:"OK"});
  const store=state.activeStore;
  await refreshPresenceForRows(rows,{force:true});
  if(rows.length>500&&!largeSyncConfirmed){
    const approved=await openMessageModal({title:tr("operations.large_sync_background_title","Build collection in the background?"),message:trf("operations.large_sync_background_help","{count} records will be prepared once, then DerridAI will build and validate the collection as a background operation. You may continue working in this tab while the build runs.",{count:rows.length.toLocaleString()}),confirmLabel:tr("operations.start_background_build","Start background build"),cancelLabel:tr("ui.cancel","Cancel")});
    if(!approved)return false;
  }
  const items=await buildUpsertItems(rows,store,{yieldEvery:rows.length>500?80:0});
  try{
    const transportItems=items.map(item=>({
      key:item.key,
      record:upsertRecordPayload(item.record),
      fingerprint:item.fingerprint,
      chroma_id:item.chroma_id,
      file_name:item.file_name,
      audit_entries:item.audit_entries||[],
      replace_updates:item.replace_updates,
      updates_count:item.updates_count,
    }));
    const sourceWorks=[...new Set(rows.map(row=>String(row.record?.work||row.file?.records?.[row.index]?.work||"").trim()).filter(Boolean))];
    const job=await api("/api/jobs/upsert",{method:"POST",body:JSON.stringify({store_name:store,items:transportItems,document_field:"text",embedding_field:"embedding",batch_size:500,mirror_languages:true,label:labelText,source_kind:"browser_workspace",source_label:labelText,source_works:sourceWorks})});
    state.jobs=[job,...state.jobs.filter(existing=>existing.id!==job.id)];
    syncJobProgressToasts();startJobPolling();
    toast(trf("operations.vector_build_queued","Queued {count} records for background build of {store}",{count:rows.length.toLocaleString(),store}),{tone:"success"});
    notifyVectorStoresChanged();
    if(state.view==="home")refreshOperationsPanelOnly();
    return true;
  }catch(error){toast(`Could not start vector build: ${error.message}`);return false}
}

function rowsFromReviewSelection(){
  return selectedReviewItems().map(item=>({file:item.file,record:item.file.records[item.index],index:item.index}));
}
function linkedPdfRows(page=state.pdf.page){
  return allRows().filter(({record})=>pdfLinks(record).some(link=>{
    if(Number(link.pdf_page)!==Number(page))return false;
    return !state.pdf.name||link.pdf_file===state.pdf.name;
  }));
}
async function linkPdfPage(file,index,page){
  if(!state.pdf.name)return toast("Open a PDF first");
  const record=file.records[index];
  let links=pdfLinks(record);
  const target={pdf_file:state.pdf.name,pdf_page:Number(page)};
  if(links.some(link=>link.pdf_file===target.pdf_file&&Number(link.pdf_page)===target.pdf_page))return toast(`Record is already linked to page ${page}`);
  if(links.length&&links.some(link=>link.pdf_file!==target.pdf_file)){
    if(!await openMessageModal({title:"Replace PDF links?",message:`This record is linked to ${links[0].pdf_file}. Replace those PDF links with ${target.pdf_file}?`,tone:"danger",confirmLabel:"Replace links",cancelLabel:"Cancel"}))return;
    links=[];
  }
  const next=[...links,target].sort((a,b)=>a.pdf_page-b.pdf_page);
  const count=applyRecordChanges(file,index,normalizePdfLinkChanges(record,next),{source:"pdf_link"});
  shell();renderView();
  toast(count?`Linked record to PDF page ${page}`:"PDF link unchanged");
}
function unlinkPdfLink(file,index,link,{stayInPdf=false}={}){
  const record=file?.records?.[index];
  if(!record)return;
  const links=pdfLinks(record);
  const next=links.filter(item=>!(item.pdf_file===link.pdf_file&&Number(item.pdf_page)===Number(link.pdf_page)));
  if(next.length===links.length)return toast("That PDF link was not found");
  const count=applyRecordChanges(file,index,normalizePdfLinkChanges(record,next),{source:"pdf_unlink"});
  if(stayInPdf)renderPdf(document.querySelector("#main"));
  else{shell();renderView()}
  toast(count?`Unlinked ${link.pdf_file} page ${link.pdf_page}`:"PDF link unchanged");
}
function unlinkAllPdfLinks(file,index){
  const record=file?.records?.[index];
  if(!record||!pdfLinks(record).length)return toast("This record has no PDF links");
  const count=applyRecordChanges(file,index,normalizePdfLinkChanges(record,[]),{source:"pdf_unlink"});
  shell();renderView();
  toast(count?"All PDF links removed":"No PDF links changed");
}

function viewLabel(view){
  return viewConfig.find(item=>item.id===view)?.label||view;
}
function navSnapshot(){
  const file=activeFile();
  return {
    view:state.view,
    activeFileId:state.activeFileId,
    selectedIndex:file?selectedIndex(file):0,
    activeStore:state.activeStore||"",
    storeWork:state.storeWork||"",
    storePage:state.storePage||1,
    storeBrowseMode:state.storeBrowseMode||"works",
    pdfPage:state.pdf.page||1,
    // Breadcrumb back/forward restores the same state that a copied URL does,
    // rather than only restoring the page shell.
    urlState:cloneAuditValue(currentTableUrlState(state.view)),
  };
}
function sameSnapshot(a,b){
  if(!a||!b)return false;
  return JSON.stringify(a)===JSON.stringify(b);
}
function applyNavSnapshot(target){
  if(!target)return;
  if(target.activeFileId&&state.files.some(file=>file.id===target.activeFileId))state.activeFileId=target.activeFileId;
  state.view=target.view||"home";
  if(state.activeFileId&&Number.isFinite(+target.selectedIndex))state.selected[state.activeFileId]=+target.selectedIndex;
  if(target.activeStore!==undefined)state.activeStore=target.activeStore||"";
  if(target.storeWork!==undefined)state.storeWork=target.storeWork||"";
  if(Number.isFinite(+target.storePage))state.storePage=Math.max(1,+target.storePage);
  if(target.storeBrowseMode)state.storeBrowseMode=target.storeBrowseMode;
  if(Number.isFinite(+target.pdfPage))state.pdf.page=Math.max(1,+target.pdfPage);
  if(target.urlState)applyCompressedTableUrlState(target.urlState,state.view);
}
const viewPathMap={home:"/",list:"/records",record:"/record",works:"/works",global:"/search",annotations:"/annotations",pdf:"/pdf",compare:"/compare",vector:"/databases",rag:"/rag",faq:"/faq",responsecache:"/response-cache",providers:"/providers",config:"/settings"};
const pathViewMap=Object.fromEntries(Object.entries(viewPathMap).map(([view,path])=>[path,view]));
let urlSyncHook=null;
function setUrlSyncHook(hook){urlSyncHook=typeof hook==="function"?hook:null}
function currentTableUrlState(view=state.view){
  // URL state is intentionally view-scoped. It is the public/shareable state
  // contract for a page; IndexedDB remains only a convenience for restoring a
  // user's workspace when no URL overrides are present.
  if(view==="list"){
    const f=activeFile();if(!f)return null;
    return {c:state.tableColumns.list||null,s:state.sorts[f.id]||null,f:state.listFilters[f.id]||null,p:state.pages[f.id]||1,z:state.pageSize,q:state.searches[f.id]||""};
  }
  if(view==="global")return {c:state.tableColumns.global||null,s:state.globalSort,f:state.globalFilters,sf:state.searchFacetFilters||{},p:state.globalPage,z:state.pageSize,q:state.globalSearch,m:state.globalSearchMode,dm:state.dbSearchMethod,dw:state.dbSearchWhere,dk:state.dbSearchFetchK,dl:state.dbSearchLambda,ao:Boolean(state.globalAdvancedOpen),l:state.searchResultLayouts};
  if(view==="vector")return {c:state.tableColumns.vector||null,s:state.storeSort,f:state.storeFilters,p:state.storePage,z:state.storePageSize,w:state.storeWork,b:state.storeBrowseMode,ss:state.storeSearchSort,q:state.storeQuery};
  if(view==="works")return {q:state.worksSearch||"",w:state.workOverview||""};
  if(view==="annotations")return {q:state.annotationSearch||"",m:state.annotationView||"works"};
  if(view==="home")return {m:Number(state.dashboardMetricIndex)||0,sm:state.globalSearchMode||"traditional",q:state.globalSearch||""};
  if(view==="record")return {q:state.recordFind||"",rr:state.researcherRecordId||""};
  if(view==="faq")return {q:state.faqSearch||"",p:state.faqPage||1};
  return null;
}
function applyCompressedTableUrlState(value,view=state.view){
  if(!value||typeof value!=="object")return;
  if(view==="list"){
    const f=activeFile();if(!f)return;
    if(Array.isArray(value.c))state.tableColumns.list=value.c;
    if(value.s)state.sorts[f.id]=value.s;
    if(value.f&&typeof value.f==="object")state.listFilters[f.id]=value.f;
    if(Number.isFinite(+value.p))state.pages[f.id]=Math.max(1,+value.p);
    if(Number.isFinite(+value.z))state.pageSize=Math.max(10,+value.z);
    if(typeof value.q==="string")state.searches[f.id]=value.q;
  }else if(view==="global"){
    if(Array.isArray(value.c))state.tableColumns.global=value.c;
    if(value.s)state.globalSort=value.s;
    if(Array.isArray(value.f))state.globalFilters=value.f;
    if(value.sf&&typeof value.sf==="object"&&!Array.isArray(value.sf))state.searchFacetFilters=Object.fromEntries(Object.entries(value.sf).map(([field,values])=>[field,Array.isArray(values)?values.map(String):[]]).filter(([,values])=>values.length));
    if(Number.isFinite(+value.p))state.globalPage=Math.max(1,+value.p);
    if(Number.isFinite(+value.z))state.pageSize=Math.max(10,+value.z);
    if(typeof value.q==="string")state.globalSearch=value.q;
    if(["traditional","database"].includes(value.m))state.globalSearchMode=value.m;
    if(["similarity","mmr","filter"].includes(value.dm))state.dbSearchMethod=value.dm;
    if(value.dw&&typeof value.dw==="object"&&!Array.isArray(value.dw))state.dbSearchWhere=value.dw;
    if(Number.isFinite(+value.dk))state.dbSearchFetchK=Math.max(1,+value.dk);
    if(Number.isFinite(+value.dl))state.dbSearchLambda=Math.max(0,Math.min(1,+value.dl));
    if(typeof value.ao==="boolean")state.globalAdvancedOpen=value.ao;
    if(value.l&&typeof value.l==="object")state.searchResultLayouts={...state.searchResultLayouts,...value.l};
    if(state.globalSearchMode==="database"&&(state.globalSearch||Object.keys(dbSearchWhere()).length))state.globalSearchAutoRun=true;
  }else if(view==="vector"){
    if(Array.isArray(value.c))state.tableColumns.vector=value.c;
    if(value.s)state.storeSort=value.s;
    if(value.f&&typeof value.f==="object")state.storeFilters=value.f;
    if(Number.isFinite(+value.p))state.storePage=Math.max(1,+value.p);
    if(Number.isFinite(+value.z))state.storePageSize=Math.max(10,+value.z);
    if(typeof value.w==="string")state.storeWork=value.w;
    if(["works","records"].includes(value.b))state.storeBrowseMode=value.b;
    if(value.ss)state.storeSearchSort=value.ss;
    if(typeof value.q==="string")state.storeQuery=value.q;
  }else if(view==="works"){
    if(typeof value.q==="string")state.worksSearch=value.q;
    if(typeof value.w==="string")state.workOverview=value.w;
  }else if(view==="annotations"){
    if(typeof value.q==="string")state.annotationSearch=value.q;
    if(["works","recent"].includes(value.m))state.annotationView=value.m;
  }else if(view==="home"){
    if(Number.isFinite(+value.m))state.dashboardMetricIndex=Math.max(0,+value.m);
    if(["traditional","database"].includes(value.sm))state.globalSearchMode=value.sm;
    if(typeof value.q==="string")state.globalSearch=value.q;
  }else if(view==="record"){
    if(typeof value.q==="string")state.recordFind=value.q;
    if(typeof value.rr==="string")state.researcherRecordId=value.rr;
  }else if(view==="faq"){
    if(typeof value.q==="string")state.faqSearch=value.q;
    if(Number.isFinite(+value.p))state.faqPage=Math.max(1,+value.p);
  }
}

function urlFromState(){
  const url=new URL(location.href);
  const params=url.searchParams;
  for(const key of ["view","file","record","store","work","dbpage","browse","pdfpage","ts"])params.delete(key);
  params.set("view",state.view||"home");
  if(state.activeFileId)params.set("file",state.activeFileId);
  const file=activeFile();
  if(file&&Number.isFinite(selectedIndex(file)))params.set("record",String(selectedIndex(file)));
  if(state.activeStore)params.set("store",state.activeStore);
  if(state.storeWork)params.set("work",state.storeWork);
  if(state.storePage>1)params.set("dbpage",String(state.storePage));
  if(state.storeBrowseMode&&state.storeBrowseMode!=="works")params.set("browse",state.storeBrowseMode);
  if(state.view==="pdf"&&state.pdf.page>1)params.set("pdfpage",String(state.pdf.page));
  const tableState=currentTableUrlState();
  if(tableState){const compressed=compressUrlState(tableState);if(compressed)params.set("ts",compressed)}
  const path=viewPathMap[state.view]||"/";
  const query=params.toString();
  return `${path}${query?`?${query}`:""}${url.hash}`;
}
function syncUrl({replace=false,href=null}={}){
  href=href||urlFromState();
  const current=`${location.pathname}${location.search}${location.hash}`;
  if(href===current)return;
  const snapshot=navSnapshot();
  if(urlSyncHook){urlSyncHook(href,{replace,snapshot});return}
  try{
    history[replace?"replaceState":"pushState"](snapshot,"",href);
  }catch(error){console.warn("Could not update browser URL state",error)}
}
function applyUrlState(){
  const params=new URLSearchParams(location.search);
  const pathView=pathViewMap[location.pathname];
  const view=pathView||params.get("view");
  if(view&&viewConfig.some(item=>item.id===view))state.view=view;
  const file=params.get("file");
  // A file parameter is authoritative. If the referenced browser-local JSONL
  // is not loaded yet, show the corpus-workspace CTA instead of silently
  // substituting another file from IndexedDB. Once the same content is loaded,
  // its stable content-derived id lets the rest of the URL state apply.
  if(file)state.activeFileId=state.files.some(item=>item.id===file)?file:null;
  const record=Number(params.get("record"));
  if(state.activeFileId&&Number.isInteger(record)&&record>=0)state.selected[state.activeFileId]=record;
  const store=params.get("store");
  if(store)state.activeStore=store;
  const work=params.get("work");
  if(work!==null)state.storeWork=work;
  const dbPage=Number(params.get("dbpage"));
  if(Number.isFinite(dbPage)&&dbPage>0)state.storePage=dbPage;
  const browse=params.get("browse");
  if(["works","records"].includes(browse))state.storeBrowseMode=browse;
  const pdfPage=Number(params.get("pdfpage"));
  if(Number.isFinite(pdfPage)&&pdfPage>0)state.pdf.page=pdfPage;
  const compressed=params.get("ts");
  if(compressed)applyCompressedTableUrlState(decompressUrlState(compressed));
}
function navigateTo(view,{fileId=null,index=null,push=true,href=null}={}){
  if(!canAccessPage(view))view="home";
  // Research performs an authoritative store refresh on entry. Do not redirect
  // from this legacy navigation bridge using the cached hasCorpusDb() value; a
  // newly created/restored collection may not have reached shell state yet.
  const before=navSnapshot();
  if(push){
    const last=state.navHistory[state.navHistory.length-1];
    if(!sameSnapshot(last,before)){
      state.navHistory.push(before);
      if(state.navHistory.length>50)state.navHistory.shift();
    }
    state.navForward=[];
  }
  if(fileId&&state.files.some(file=>file.id===fileId))state.activeFileId=fileId;
  if(index!==null&&state.activeFileId)state.selected[state.activeFileId]=Number(index);
  if(state.view==="vector"&&view!=="vector"){
    // Store pages/search results duplicate records already persisted in Chroma.
    // Drop those transient copies when leaving Vector Stores.
    state.storeRecords=[];
    state.storeSearchResults=[];
  }
  state.view=view;
  persistPrefs();
  syncUrl({replace:!push,href});
  shell();
  renderView();
}
function goBack(){
  while(state.navHistory.length){
    const target=state.navHistory.pop();
    if(!target)continue;
    if(target.activeFileId&&!state.files.some(file=>file.id===target.activeFileId))continue;
    state.navForward.push(navSnapshot());
    if(state.navForward.length>50)state.navForward.shift();
    applyNavSnapshot(target);
    persistPrefs();syncUrl({replace:true});shell();renderView();return;
  }
}
function goForward(){
  while(state.navForward.length){
    const target=state.navForward.pop();
    if(!target)continue;
    if(target.activeFileId&&!state.files.some(file=>file.id===target.activeFileId))continue;
    state.navHistory.push(navSnapshot());
    applyNavSnapshot(target);
    persistPrefs();syncUrl({replace:true});shell();renderView();return;
  }
}










// Names of the facts shown for an operation (panel rows and the details dialog), translated at render time.


async function warmupProviderProfile(profileId=null){
  const profile=providerProfile(profileId||state.appConfig.default_provider_profile);
  if(!profile)return;
  const current=state.providerWarmups?.[profile.id]||{};
  if(current.status==="running")return;
  const cfg=providerRequestConfig(profile,{textReview:false});
  const started=performance.now();
  const startedAt=new Date().toISOString();
  const running={
    status:"running",message:`Warming ${cfg.model}…`,profile_id:profile.id,
    provider:profile.type,model:cfg.model,base_url:cfg.base_url,
    started_at:startedAt,completed_at:null,elapsed_seconds:null,error:null,
  };
  state.providerWarmups[profile.id]=running;
  if(profile.id===state.appConfig.default_provider_profile)state.warmup=running;
  if(state.view==="home")renderDashboard(document.querySelector("#main"));
  try{
    const result=await api("/api/llm/warmup",{method:"POST",body:JSON.stringify({
      provider:profile.type,model:cfg.model,base_url:cfg.base_url,api_key:cfg.api_key,
      // Load with the context real calls use, so the model is not loaded twice.
      num_ctx:Number(cfg.ollama?.num_ctx)>0?Number(cfg.ollama.num_ctx):undefined,
    })});
    const ready={
      status:"ready",message:`${providerDisplayName(profile)} · ${result.model||cfg.model} warmed`,
      profile_id:profile.id,provider:profile.type,model:result.model||cfg.model,
      base_url:result.base_url||cfg.base_url,started_at:startedAt,completed_at:new Date().toISOString(),
      elapsed_seconds:(performance.now()-started)/1000,error:null,
    };
    state.providerWarmups[profile.id]=ready;
    if(profile.id===state.appConfig.default_provider_profile)state.warmup=ready;
  }catch(error){
    const failed={
      status:"failed",message:error.message,profile_id:profile.id,provider:profile.type,model:cfg.model,
      base_url:cfg.base_url,started_at:startedAt,completed_at:new Date().toISOString(),
      elapsed_seconds:(performance.now()-started)/1000,error:error.message,
    };
    state.providerWarmups[profile.id]=failed;
    if(profile.id===state.appConfig.default_provider_profile)state.warmup=failed;
  }
  if(state.view==="home")renderDashboard(document.querySelector("#main"));
}

async function warmupConfiguredLlm(){
  return warmupProviderProfile(state.appConfig.default_provider_profile);
}








// ---- Operations panel bridge -------------------------------------------------------------
// The panel itself is a Vue component (components/OperationsPanel.vue). The runtime still owns
// job state, the dock, toasts, and the details/results dialogs, so the panel reads a plain view
// model from here and calls back into the existing functions.
function notifyOperationsChanged(){
  touchJobs();
}
function operationsBridge(){
  return {
    snapshot:()=>(state.jobs||[]).map(operationViewModel),
    subscribe:listener=>subscribeToJobChanges(listener),
    refresh:async()=>{await refreshJobs({rerender:true})},
    openDetails:id=>{void openJobDetails(id)},
    openResult:id=>{void openJobResults(id)},
    cancel:async id=>{await cancelBackgroundJob(id)},
    remove:async id=>{
      await api(`/api/jobs/${encodeURIComponent(id)}`,{method:"DELETE"});
      pruneClientJobState(id);
      persistPrefs();
      await refreshJobs({rerender:true});
    },
    clearFinished:async()=>{
      await api("/api/jobs",{method:"DELETE"});
      await refreshJobs({rerender:true});
    },
  };
}
function renderOperationsPanel(){
  // A placeholder only: the Vue panel is mounted into it by mountOperationsPanelHost().
  return `<div id="operationsPanelHost"></div>`;
}
function mountOperationsPanelHost(){
  mountOperationsPanel(document.querySelector("#operationsPanelHost"),operationsBridge());
}
function refreshOperationsPanelOnly(){
  notifyOperationsChanged();
  if(state.view==="rag")refreshRagProgressPanel();
}
function wireCorpusBuildsHomeCard(root=document){
  root.querySelector("#dashCorpusBuilder")?.addEventListener("click",()=>window.dispatchEvent(new CustomEvent("derridai:navigate-native",{detail:{path:"/pdf?mode=builder",runtimeView:"pdf"}})));
  root.querySelectorAll("[data-dashboard-corpus-build]").forEach(button=>button.addEventListener("click",()=>openJobResults(button.dataset.dashboardCorpusBuild)));
}
function refreshCorpusBuildsHomeCardOnly(){
  const current=document.querySelector(".dashboard-corpus-builds");
  if(!current)return;
  const holder=document.createElement("div");
  holder.innerHTML=renderCorpusBuildsHomeCard();
  const replacement=holder.firstElementChild;
  if(replacement)current.replaceWith(replacement);
  wireCorpusBuildsHomeCard();
}




async function gradeRagResponse({
  question,
  answer,
  evidence=[],
  responseRecordId=null,
  generationProvider=null,
  generationModel=null,
}){
  openLlmTaskLauncher({
    task:"rag_grade",
    title:"Analyze & grade RAG response",
    description:"Grade relevance, source binding, attribution, fidelity, precision, coverage, and interpretive usefulness.",
    contextText:question,
    generationProvider,
    generationModel,
    payload:{
      question,answer,evidence:ragGradeEvidencePayload(evidence),response_record_id:responseRecordId,
      generation_provider:generationProvider,
      generation_model:generationModel,
    },
    onForegroundResult:async result=>{
      const dialog=document.createElement("dialog");dialog.className="rag-grade-dialog";
      dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">RAG response grade</h2><div class="dialog-subtitle">Saved with the cached RAG query when a response-cache record is available.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db">${ragGradeHtml(result.grade||{})}</div><div class="da"><button class="btn" data-close>Close</button></div>`;
      document.body.appendChild(dialog);showAppModal(dialog);const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
    },
  });
}


async function removeRagJob(jobId){
  const job=state.jobs.find(item=>item.id===jobId);
  if(!job)return pruneClientJobState(jobId);
  if(["queued","running","cancelling"].includes(job.status))return toast("Cancel the RAG pipeline before removing it");
  const approved=await openMessageModal({
    title:"Remove RAG pipeline result?",
    message:`Remove this ${job.status} RAG pipeline and its retained result from activity history?`,
    tone:"danger",confirmLabel:"Remove pipeline",cancelLabel:"Cancel",
  });
  if(!approved)return;
  try{
    await api(`/api/jobs/${encodeURIComponent(jobId)}`,{method:"DELETE"});
    pruneClientJobState(jobId);persistPrefs();
    refreshRagProgressPanel();
    if(state.view==="home")refreshOperationsPanelOnly();
    toast("RAG pipeline removed");
  }catch(error){
    if(String(error?.message||"").includes("404")){pruneClientJobState(jobId);persistPrefs();refreshRagProgressPanel();return toast("RAG pipeline was already removed")}
    openMessageModal({title:"Could not remove RAG pipeline",message:error.message,tone:"danger"});
  }
}

async function clearFinishedRagJobs(){
  const finished=state.jobs.filter(job=>job.type==="rag"&&!["queued","running","cancelling"].includes(job.status));
  if(!finished.length)return toast("There are no past RAG results to clear");
  if(!await openMessageModal({title:"Clear past RAG results?",message:`Clear ${finished.length} finished RAG operation${finished.length===1?"":"s"} and their retained results?`,tone:"danger",confirmLabel:"Clear results",cancelLabel:"Cancel"}))return;
  let removed=0,failed=0;
  for(const job of finished){
    try{
      await api(`/api/jobs/${encodeURIComponent(job.id)}`,{method:"DELETE"});
      pruneClientJobState(job.id);
      removed++;
    }catch(error){
      failed++;
      console.warn("Could not remove RAG job",job.id,error);
    }
  }
  await refreshJobs();
  refreshRagProgressPanel();
  toast(`Cleared ${removed} past RAG result${removed===1?"":"s"}${failed?` · ${failed} could not be removed`:""}`);
}

const RAG_STAGE_ORDER=[
  ["query_metadata","Query decomposition"],
  ["retrieval","Vector retrieval"],
  ["deduplicate","Deduplication / rank fusion"],
  ["rerank","Reranking"],
  ["context","Evidence packaging"],
  ["generation","Answer generation"],
  ["bind_sources","Citation/source binding"],
  ["response_cache","Response cache"],
  ["auto_grade","Automatic grade"],
];
function ragProgressPanelHtml(){
  const allRagJobs=state.jobs.filter(job=>job.type==="rag");
  const jobs=allRagJobs.slice(0,12);
  const activeCount=allRagJobs.filter(job=>["queued","running","cancelling"].includes(job.status)).length;
  const finishedCount=allRagJobs.length-activeCount;
  return `<section class="card rag-live-panel" id="ragProgressPanel">
    <div class="cardhead"><div><b>RAG pipeline activity</b><div class="note">${activeCount} active · ${finishedCount} past result${finishedCount===1?"":"s"} · stage, model, parameters, and timing refresh automatically</div></div><div class="tools"><button class="btn small" id="ragRefreshJobs">${icon("refresh")}Refresh</button>${finishedCount?'<button class="btn small danger" id="ragClearFinished">Clear past results</button>':""}</div></div>
    <div class="rag-live-jobs">${jobs.map(job=>{
      const active=["queued","running","cancelling"].includes(job.status);
      const request=job.request||{};
      const stageOrder=RAG_STAGE_ORDER.filter(([stage])=>stage!=="auto_grade"||request.auto_grade);
      const stageIndex=stageOrder.findIndex(([stage])=>stage===job.stage);
      const generation=request.generation||{};
      const elapsed=humanDuration(jobElapsedSeconds(job));
      const totalLabel=job.finished_at?`Total ${elapsed}`:`Elapsed ${elapsed}`;
      const sourceStore=state.stores.find(store=>store.name===job.source_collection);
      const stageEvents=(job.events||[]).filter(event=>event.stage===job.stage&&event.timestamp);
      const stageStart=stageEvents.length?new Date(stageEvents[0].timestamp).getTime():null;
      const stageElapsed=Number.isFinite(stageStart)?humanDuration(Math.max(0,(Date.now()-stageStart)/1000)):"—";
      const params=[
        `started by ${job.owner||"—"}`,
        `provider ${job.provider||"—"}`,
        `generation ${job.model||"—"}`,
        `embedding ${sourceStore?.embedding_model||sourceStore?.embedding_provider||"—"}`,
        `reranker model ${request.cross_encoder_model||request.reranker||"—"}`,
        `languages ${(request.locales||[]).join("+")||"—"}`,
        `retrieval ${(request.search_types||[]).join("+")||"—"}`,
        `k ${request.k??"—"}`,
        `fetch ${request.fetch_k??"—"}`,
        `λ ${request.lambda_mult??"—"}`,
        `RRF ${request.rrf_k??"—"}`,
        `topN ${request.rerank_top_n??"—"}`,
        `auto-grade ${request.auto_grade?"on":"off"}`,
        `num_ctx ${generation.num_ctx??"—"}`,
        `num_predict ${generation.num_predict??"—"}`,
        job.provider==="openai"
          ?"scheduler uncapped"
          :`scheduler ${job.scheduling?.active_when_started??state.health?.rag_concurrency?.ollama_active??"—"}/${job.scheduling?.limit??state.appConfig.ollama_rag_concurrency??1}`,
        `stage time ${stageElapsed}`,
      ];
      return `<article class="rag-live-job">
        <div class="rag-live-job-head"><div><b>${esc(job.prompt||"RAG query")}</b><span>${esc(job.source_collection||"")} · ${esc(job.model||job.provider||"")} · ${esc(totalLabel)}</span></div><span class="job-status ${esc(job.status)}">${esc(job.status)}</span></div>
        <div class="rag-live-params">${params.map(value=>`<span>${esc(value)}</span>`).join("")}</div>
        <div class="rag-stage-rail">${stageOrder.map(([stage,name],index)=>{
          const done=job.status==="completed"||index<stageIndex;
          const current=active&&index===stageIndex;
          return `<div class="rag-stage-node ${done?"done":""} ${current?"current":""}"><i>${done?"✓":index+1}</i><div><b>${esc(name)}</b><span>${current?esc(job.stage_detail||"Running…"):done?"Complete":"Pending"}</span></div></div>`;
        }).join("")}</div>
        <div class="rag-live-detail">${job.status==="cancelling"||job.cancel_requested?"Cancellation requested · waiting for the current pipeline call to reach a safe checkpoint.":esc(job.stage_detail||job.fatal_error||"Queued")}</div>
        <div class="rag-live-footer"><div class="rag-live-timing"><span>${esc(totalLabel)}</span><span>${job.started_at?`Started ${esc(formatTimestamp(job.started_at))}`:"Not started"}</span>${job.finished_at?`<span>Finished ${esc(formatTimestamp(job.finished_at))}</span>`:""}</div><div class="tools"><button class="btn small" data-rag-job-details="${job.id}">Details / timeline</button>${job.status==="completed"?`<button class="btn small primary" data-rag-job-result="${job.id}">Open result</button>`:""}${active?(job.cancel_requested||job.status==="cancelling"?'<button class="btn small" disabled>Cancelling…</button>':`<button class="btn small danger" data-rag-job-cancel="${job.id}">Cancel</button>`):`<button class="btn small danger" data-rag-job-remove="${job.id}">Remove</button>`}</div></div>
      </article>`;
    }).join("")||'<div class="llm-empty">No RAG jobs yet. Start one below.</div>'}</div>
  </section>`;
}

function wireRagProgressPanel(){
  const panel=document.querySelector("#ragProgressPanel");
  if(!panel)return;
  panel.querySelector("#ragRefreshJobs")?.addEventListener("click",()=>refreshJobs());
  panel.querySelector("#ragClearFinished")?.addEventListener("click",clearFinishedRagJobs);
  panel.querySelectorAll("[data-rag-job-details]").forEach(button=>button.onclick=()=>openJobDetails(button.dataset.ragJobDetails));
  panel.querySelectorAll("[data-rag-job-result]").forEach(button=>button.onclick=()=>openJobResults(button.dataset.ragJobResult));
  panel.querySelectorAll("[data-rag-job-cancel]").forEach(button=>button.onclick=()=>cancelBackgroundJob(button.dataset.ragJobCancel));
  panel.querySelectorAll("[data-rag-job-remove]").forEach(button=>button.onclick=()=>removeRagJob(button.dataset.ragJobRemove));
}
function refreshRagProgressPanel(){
  const current=document.querySelector("#ragProgressPanel");
  if(!current)return;
  const holder=document.createElement("div");
  holder.innerHTML=ragProgressPanelHtml();
  const replacement=holder.firstElementChild;
  if(replacement)current.replaceWith(replacement);
  wireRagProgressPanel();
}

function compactNumber(value){const n=Number(value)||0;if(n>=1000000)return `${(n/1000000).toFixed(n>=10000000?0:1)}M`;if(n>=1000)return `${(n/1000).toFixed(n>=100000?0:1)}K`;return n.toLocaleString()}
function relativeTime(value){const date=new Date(value||0);if(!Number.isFinite(date.getTime()))return tr("time.recently","Recently");const seconds=Math.max(0,Math.round((Date.now()-date.getTime())/1000));if(seconds<60)return tr("time.just_now","just now");const minutes=Math.round(seconds/60);if(minutes<60)return trf("time.minutes_ago","{count} min ago",{count:minutes});const hours=Math.round(minutes/60);if(hours<24)return trf("time.hours_ago","{count} hr ago",{count:hours});return trf("time.days_ago","{count} d ago",{count:Math.round(hours/24)})}


function renderCorpusBuildsHomeCard(){
  if(isResearcher())return "";
  const builds=(state.jobs||[]).filter(job=>job.type==="pdf_corpus").slice(0,4);
  const active=builds.filter(job=>["queued","running","cancelling"].includes(job.status)).length;
  return `<section class="card dashboard-corpus-builds" aria-label="${esc(tr("pdf_corpus.home_title","Corpus builds"))}">
    <div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("pdf")}</span><b>${esc(tr("pdf_corpus.home_title","Corpus builds"))}</b>${active?`<span class="dashboard-corpus-active">${active} ${esc(tr("operations.active","active"))}</span>`:""}</div><button class="dashboard-text-link" id="dashCorpusBuilder">${esc(tr("pdf_corpus.open_builder","Open Corpus Builder"))} →</button></div>
    <p class="dashboard-corpus-help">${esc(tr("pdf_corpus.home_help","Recent PDF-to-corpus pipelines stay visible here even after you leave Corpus Builder."))}</p>
    <div class="dashboard-corpus-list">${builds.length?builds.map(job=>{const pct=Math.max(0,Math.min(100,Math.round(Number(job.progress||0)*100)));const status=job.raw_status||job.status||"unknown";return `<button type="button" class="dashboard-corpus-row" data-dashboard-corpus-build="${esc(job.id)}"><span class="dashboard-corpus-state ${esc(job.status||"")}" aria-hidden="true"></span><span class="dashboard-corpus-copy"><b>${esc(job.source_filename||tr("pdf_corpus.source_pdf","Source PDF"))}</b><small>${esc(String(status).replaceAll("_"," "))} · ${esc(String(job.stage_detail||job.stage||""))}</small></span><span class="dashboard-corpus-progress"><b>${pct}%</b><i><span style="width:${pct}%"></span></i></span></button>`}).join(""):`<div class="dashboard-corpus-empty">${esc(tr("pdf_corpus.home_empty","No corpus builds yet. Start with a source PDF in Corpus Builder."))}</div>`}</div>
  </section>`;
}



let shellRefreshHook=()=>{};
function setShellRefreshHook(hook){
  shellRefreshHook=typeof hook==="function"?hook:()=>{};
}
function shell(){
  persistPrefs();
  shellRefreshHook();
}
function collapseKeyFor(element,index){
  const heading=element.querySelector(".cardhead b,.cardhead h2,.section-title-row h3,.dash-chart-title")?.textContent?.trim()
    ||element.getAttribute("aria-label")
    ||element.className
    ||element.tagName;
  return `${state.view}::${heading}::${index}`;
}
function enhanceCollapsibles(root=document.querySelector("#main")){
  if(!root)return;
  const targets=[...root.querySelectorAll(".card:not(.work):not(.faq-card),.card-inset,.dash-chart,.provider-profile-card,.rag-live-job")];
  targets.forEach((element,index)=>{
    if(element.dataset.collapsibleReady==="1"||element.closest("dialog")||element.matches("[data-no-collapse=true]")||element.closest("[data-no-collapse=true]"))return;
    let host=element.querySelector(":scope > .cardhead")
      ||element.querySelector(":scope > .dash-chart-head")
      ||element.querySelector(":scope > .provider-profile-card-head")
      ||element.querySelector(":scope > .rag-live-job-head")
      ||element.querySelector(":scope > .section-title-row");
    if(!host)return;
    const fullHeight=Math.max(element.scrollHeight,element.getBoundingClientRect().height);
    const headerHeight=Math.max(30,host.getBoundingClientRect().height||30);
    if(fullHeight<=headerHeight*2){
      element.dataset.collapsibleReady="skip";
      return;
    }
    element.dataset.collapsibleReady="1";
    const key=collapseKeyFor(element,index);
    element.dataset.collapseKey=key;
    const collapsed=Boolean(state.collapsedPanels?.[key]);
    element.classList.toggle("ui-collapsed",collapsed);
    const compactTitle=document.createElement("span");
    compactTitle.className="ui-collapse-title";
    compactTitle.textContent=
      element.querySelector(":scope > .cardhead b,:scope > .dash-chart-head .dash-chart-title,:scope > .section-title-row h3,:scope > .rag-live-job-head b")?.textContent?.trim()
      ||element.querySelector(":scope > .provider-profile-card-head [data-profile-field='name']")?.value
      ||element.querySelector("h1,h2,h3,h4,b")?.textContent?.trim()
      ||"Section";
    host.appendChild(compactTitle);
    const button=document.createElement("button");
    button.type="button";button.className="ui-collapse-toggle";button.title=collapsed?"Expand":"Collapse";button.setAttribute("aria-label",button.title);button.textContent=collapsed?"＋":"−";
    button.onclick=e=>{e.stopPropagation();const next=!element.classList.contains("ui-collapsed");element.classList.toggle("ui-collapsed",next);button.textContent=next?"＋":"−";button.title=next?"Expand":"Collapse";state.collapsedPanels[key]=next;persistPrefs()};
    host.appendChild(button);
  });
}
let collapsibleObserver=null;
function renderView(){
  const main=document.querySelector("#main");
  // Native Vue routes (for example Users & roles) intentionally do not mount
  // the legacy surface. Do not let compatibility rendering or URL syncing
  // overwrite those routes while they are active.
  if(!main){
    unmountOperationsPanel();
    shellRefreshHook?.();
    return null;
  }
  if(state.view!=="home")unmountOperationsPanel();
  if(!canAccessPage(state.view))state.view="home";
  syncUrl({replace:true});
  let result;
  if(state.view==="home") result=renderDashboard(main);
  else if(state.view==="pdf") result=renderPdf(main);
  else if(state.view==="responsecache") result=renderResponseCache(main);
  else result=null;
  Promise.resolve(result).finally(()=>requestAnimationFrame(()=>{enhanceCollapsibles(main);decorateDisabledControls(main);translateLegacyDom(main)}));
  return result;
}


async function importFiles(fileList){
  if(isResearcher())return toast("Researcher accounts cannot load or edit corpus files.");
  const shareParams=new URLSearchParams(location.search);
  const requestedFileId=shareParams.get("file");
  const requestedUrlState=shareParams.get("ts");
  let first=null, total=0, errors=0;
  for(const file of [...fileList]){
    const text=await file.text();
    const parsed=parseJsonl(text);
    if(!parsed.records.length){errors+=parsed.errors.length||1;continue}
    const identity=await stableJsonlFileIdentity(text);
    const existing=state.files.find(item=>item.id===identity.id);
    if(existing){
      first ||= existing.id;
      total+=existing.records.length;
      errors+=existing.errors?.length||0;
      continue;
    }
    const item={...identity,name:file.name,records:parsed.records,errors:parsed.errors,dirty:new Set(),imported_at:new Date().toISOString()};
    state.files.push(item);persistFileNow(item);first ||= item.id;total+=item.records.length;errors+=item.errors.length;
  }
  if(requestedFileId&&state.files.some(item=>item.id===requestedFileId)){
    state.activeFileId=requestedFileId;
    if(requestedUrlState)applyCompressedTableUrlState(decompressUrlState(requestedUrlState),state.view);
  }else if(first)state.activeFileId=first;
  persistPrefs();shell();renderView();syncUrl({replace:true});toast(`Loaded ${total} records${errors?` · ${errors} parse issues`:""}`);
}
async function closeFile(id){
  const f=state.files.find(x=>x.id===id);if(!f)return;
  if(f.dirty.size && !await openMessageModal({title:"Close modified JSONL?",message:`${f.name} has modified records. Close anyway?`,tone:"danger",confirmLabel:"Close file",cancelLabel:"Keep open"}))return;
  const i=state.files.indexOf(f);state.files.splice(i,1);delete state.searches[id];delete state.listFilters[id];delete state.pages[id];delete state.sorts[id];
  clearFileDerivedState(id);
  invalidateCorpusCache();
  idbDelete("files",id).catch(error=>console.error("Could not remove saved file",error));
  if(state.activeFileId===id)state.activeFileId=state.files[Math.min(i,state.files.length-1)]?.id||null;
  persistPrefs();shell();renderView();
}



function searchByMetadata(field,value,{contains=false}={}){
  const raw=String(value??"").trim();if(!field||!raw)return;state.globalPage=1;state.storeSearchResults=[];
  if(isResearcher()){state.globalSearchMode="database";state.dbSearchMethod="filter";state.dbSearchWhere={[field]:contains?{$contains:raw}:raw};state.globalSearch="";state.globalSearchAutoRun=true}else{state.globalSearchMode="traditional";state.globalSearch="";state.globalFilters=[{id:uid(),field,op:contains?"has":"eq",value:raw}]}
  persistPrefs();navigateTo("global");
}



function workflowProviderSelectHtml(selectedId){
  const profiles=providerProfiles();
  const selected=providerProfile(selectedId)||profiles[0]||null;
  if(!profiles.length)return `<div class="workflow-provider-empty"><b>${esc(tr("language.no_provider_profiles","No LLM provider profiles are configured"))}</b><p>${esc(tr("language.no_provider_profiles_help","Create a provider profile first, then return here."))}</p></div>`;
  return `<label class="workflow-field workflow-provider-select-field"><span>${esc(tr("works.provider_profile","Provider profile"))}</span><select class="control workflow-provider-select" id="workMetadataProvider">${profiles.map(profile=>`<option value="${esc(profile.id)}" ${profile.id===selected?.id?"selected":""}>${esc(providerDisplayName(profile))} · ${profile.type==="ollama"?"Ollama":"OpenAI-compatible"} · ${esc(profile.model||tr("language.model_not_set","model not set"))}${profile.id===state.appConfig.default_provider_profile?` · ${esc(tr("ui.default","Default"))}`:""}</option>`).join("")}</select><small>${esc(tr("works.provider_profile_help","Uses the same configured provider profiles as Research, PDF tools, and LLM review."))}</small></label><div class="workflow-provider-summary" id="workMetadataProviderSummary">${workflowProviderSummaryHtml(selected)}</div>`;
}
function workflowProviderSummaryHtml(profile){
  if(!profile)return "";
  return `<span class="workflow-provider-mark">${profile.type==="ollama"?"O":"AI"}</span><span><b>${esc(providerDisplayName(profile))}</b><small>${profile.type==="ollama"?"Ollama":"OpenAI-compatible"} · ${esc(profile.model||tr("language.model_not_set","model not set"))}</small><small>${Number(profile.max_concurrent_requests??1)} ${esc(tr("works.concurrent_requests","max concurrent request(s)"))}</small></span>${profile.id===state.appConfig.default_provider_profile?`<span class="provider-default-chip">${esc(tr("ui.default","Default"))}</span>`:""}`;
}

function parseProposedMetadataValue(raw,original){
  if(typeof original==="number"){const value=Number(raw);if(!Number.isFinite(value))throw new Error("Expected a number.");return value}
  if(typeof original==="boolean")return String(raw).toLowerCase()==="true";
  return raw;
}

function bulkEditRowsForScope(scope){
  if(scope==="selected")return selectedReviewItems();
  if(scope==="active"){
    const file=activeFile();
    return file?file.records.map((record,index)=>({file,record,index,key:reviewKey(file,index)})):[];
  }
  if(scope==="work"){
    const selected=selectedRecord();
    const work=selected?.work;
    return work?allRows().filter(row=>row.record.work===work):[];
  }
  return allRows();
}
const SUBSET_PROFILE_STORAGE_KEY="derridai.subset-filter-profiles.v1";
function loadSubsetProfiles(){
  try{const value=JSON.parse(localStorage.getItem(SUBSET_PROFILE_STORAGE_KEY)||"[]");return Array.isArray(value)?value:[]}catch{return []}
}
function saveSubsetProfiles(profiles){
  localStorage.setItem(SUBSET_PROFILE_STORAGE_KEY,JSON.stringify((profiles||[]).slice(0,50)));
}



function clearFileDerivedState(fileId){
  state.reviewSelection=new Set([...state.reviewSelection].filter(key=>!String(key).startsWith(fileId+"::")));
  delete state.selected[fileId];
  for(const bucket of [state.upsertState,state.upsertIgnored,state.storePresence,state.storePresenceIds,state.storePresenceCheckedAt]){
    for(const store of Object.keys(bucket||{})){
      for(const key of Object.keys(bucket[store]||{}))if(key.startsWith(fileId+"::"))delete bucket[store][key];
    }
  }
}





function dbSearchWhere(){return Object.fromEntries(Object.entries(state.dbSearchWhere||{}).filter(([,value])=>String(value??"").trim()!==""))}





const numericFilterFields=new Set(["page_start","page_end","year","publication_year","text_length","extraction_quality","attribution_confidence","semantic_classification_confidence"]);
const collectionFilterFields=new Set(["topics","concepts","persons","works_referenced","institutions_referenced","locations_referenced","events_referenced","groups_referenced","languages_referenced","document_language","quoted_speaker","quotation_chain"]);
function filterOpsForField(field){
  if(numericFilterFields.has(field))return [["eq","equals"],["neq","not equal"],["gte","greater than or equal"],["lte","less than or equal"],["empty","is empty"],["notempty","is not empty"]];
  if(collectionFilterFields.has(field))return [["has","contains"],["nhas","does not contain"],["eq","equals exactly"],["neq","does not equal"],["empty","is empty"],["notempty","is not empty"]];
  return [["eq","equals"],["neq","not equal"],["has","contains"],["nhas","does not contain"],["empty","is empty"],["notempty","is not empty"]];
}


// 0.36.10 native Search bridge. SearchView owns presentation while the runtime
// continues to own browser-local corpus state, Chroma transport, evidence
// selection, URL serialization, and the existing LLM review workflows.

/** @param {{field?: string, op?: string, value?: string}} [options] */


function recordsListMetadataSearch(field,value,contains){
  return searchByMetadata(field,value,{contains:Boolean(contains)});
}

const ligatures={"ﬀ":"ff","ﬁ":"fi","ﬂ":"fl","ﬃ":"ffi","ﬄ":"ffl","ﬅ":"ft","ﬆ":"st"};
function cleanText(text){
  let s=String(text??""),before=s;
  s=s.replace(/[ﬀﬁﬂﬃﬄﬅﬆ]/g,c=>ligatures[c]||c)
    .replace(/\u00ad/g,"")
    // eslint-disable-next-line no-misleading-character-class -- SA-15: OCR Unicode matching needs corpus fixtures before changing character semantics.
    .replace(/[\u200b\u200c\u200d\u2060\ufeff\ufffe\uffff]/g,"")
    .replace(/([A-Za-zÀ-ÖØ-öø-ÿ])-[ \t]*\r?\n[ \t]*([a-zà-öø-ÿ])/g,"$1$2")
    .replace(/\r\n/g,"\n");
  return {text:s,changed:s!==before};
}
function cleanRecord(f,i){
  const c=cleanText(f.records[i].text);if(!c.changed)return toast("No supported ligatures or artifacts found");
  const changed=applyRecordChanges(f,i,{text:c.text},{source:"ocr_cleanup"});
  shell();renderView();toast(`${changed} tracked change${changed===1?"":"s"} applied`);
}

function cleanRows(rows){
  const batchId=uid();let recordsChanged=0,fieldsChanged=0;
  for(const row of rows){
    const current=row.file.records[row.index];
    const cleaned=cleanText(current?.text);
    if(!cleaned.changed)continue;
    const n=applyRecordChanges(row.file,row.index,{text:cleaned.text},{source:"ocr_cleanup",batchId});
    if(n){recordsChanged++;fieldsChanged+=n}
  }
  shell();renderView();
  toast(`${recordsChanged} records cleaned · ${fieldsChanged} tracked changes`);
}





function fieldEditor(k,v){
  const t=Array.isArray(v)?"array":v===null?"null":typeof v;
  const full=["text","edition","review_reason","full_citation","quotation_chain"].includes(k);
  const cls=`field ${full?"field-full":""}`;
  if(t==="boolean")return `<div class="${cls}"><label>${esc(label(k))}</label><label class="boolean-control"><input data-key="${esc(k)}" data-type="boolean" type="checkbox" ${v?"checked":""}><span>${v?"Enabled":"Disabled"}</span></label></div>`;
  if(k==="text")return `<div class="${cls}"><label>${esc(label(k))}</label><textarea class="long" data-key="${esc(k)}" data-type="string">${esc(v||"")}</textarea></div>`;
  if(t==="array"||t==="object")return `<div class="${cls}"><label>${esc(label(k))} · JSON</label><textarea data-key="${esc(k)}" data-type="json">${esc(JSON.stringify(v,null,2))}</textarea></div>`;
  return `<div class="${cls}"><label>${esc(label(k))}</label><input data-key="${esc(k)}" data-type="${t}" ${t==="number"?'type="number" step="any"':""} value="${esc(v??"")}"></div>`;
}
function parseEditor(el){if(el.dataset.type==="boolean")return el.checked;if(el.dataset.type==="number")return el.value===""?null:+el.value;if(el.dataset.type==="null")return el.value===""?null:el.value;if(el.dataset.type==="json")return JSON.parse(el.value);return el.value}

function exportMenu(){
  const dialog=document.createElement("dialog");
  dialog.innerHTML=`<div class="dh"><h2 style="margin:0;font-size:16px">${esc(tr("export.title","Export JSONL"))}</h2><button class="btn" data-close>${esc(tr("ui.close","Close"))}</button></div><div class="db"><div class="tools"><button class="btn" data-export="current">${esc(tr("export.current","Current file"))}</button><button class="btn" data-export="changed">${esc(tr("export.changed","Changed files"))}</button><button class="btn" data-export="all">${esc(tr("export.all","All files separately"))}</button><button class="btn" data-export="aggregate">${esc(tr("export.aggregate","Aggregate JSONL"))}</button><button class="btn" data-export="both">${esc(tr("export.changed_aggregate","Changed + aggregate"))}</button></div></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);dialog.querySelector("[data-close]").onclick=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-export]").forEach(button=>button.onclick=()=>{doExport(button.dataset.export);dialog.close();dialog.remove()});
}
function downloadBlob(blob,name){const u=URL.createObjectURL(blob);const a=document.createElement("a");a.href=u;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),500)}
function download(name,text){downloadBlob(new Blob([text],{type:"application/x-ndjson"}),name)}
function fileJsonl(f){return f.records.map(r=>JSON.stringify(r)).join("\n")+"\n"}
function doExport(kind){
  const current=activeFile(),changed=state.files.filter(f=>f.dirty.size);
  if(kind==="current"&&current)download(current.name,fileJsonl(current));
  if(kind==="changed")changed.forEach((f,i)=>setTimeout(()=>download(f.name,fileJsonl(f)),i*160));
  if(kind==="all")state.files.forEach((f,i)=>setTimeout(()=>download(f.name,fileJsonl(f)),i*160));
  if(kind==="aggregate"||kind==="both")download("derridai-aggregate.jsonl",state.files.flatMap(f=>f.records).map(r=>JSON.stringify(r)).join("\n")+"\n");
  if(kind==="both")changed.forEach((f,i)=>setTimeout(()=>download(f.name,fileJsonl(f)),250+i*160));
}

async function currentPdfPageText(){
  const result=await extractPdfPageSmart(state.pdf.page);
  state.pdf.text=result.text;
  state.pdf.extractionSource=result.source;
  state.pdf.extractError=result.warning||"";
  return result.text||"";
}
async function applyPdfLinkMatch(match){
  if(!match?.key)return openMessageModal({title:"No supported record match",message:match?.reason||"The model did not identify a sufficiently supported record."});
  const item=reviewItemFromKey(match.key);
  if(!item)return openMessageModal({title:"Matched record unavailable",message:"The matched record is no longer loaded.",tone:"danger"});
  const confidence=Number(match.confidence);
  const approved=await openMessageModal({
    title:"Link PDF page to record?",
    message:`PDF page ${state.pdf.page} → ${item.record.record_id||"matched record"}\n\n${Number.isFinite(confidence)?`${Math.round(confidence*100)}% confidence`:"Confidence not reported"}${match.reason?`\n${match.reason}`:""}`,
    confirmLabel:"Link page",cancelLabel:"Cancel",
  });
  if(!approved)return;
  linkPdfPage(item.file,item.index,state.pdf.page);
  toast(`Linked page ${state.pdf.page} to ${item.record.record_id||"record"}`);
}
function ragGradeHtml(grade={}){
  const normalized=normalizeRagGrade(grade);
  const scoreKeys=[["query_relevance","Query relevance"],["source_binding","Source binding"],["claim_traceability","Claim traceability"],["attribution_source_discrimination","Attribution/source discrimination"],["claim_evidence_fidelity","Claim/evidence fidelity"],["conceptual_precision","Conceptual precision"],["coverage","Coverage"],["interpretive_usefulness","Interpretive usefulness"],["overall","Overall"]];
  const sections=[["Strengths",normalized.strengths],["Weaknesses",normalized.weaknesses],["Unsupported or risky claims",normalized.unsupported_or_risky_claims]];
  return `<div class="rag-grade-content"><div class="rag-grade-scores">${scoreKeys.map(([key,name])=>`<div><span>${esc(name)}</span><strong>${esc(normalized.score(key))}</strong><small>/10</small></div>`).join("")}</div><section><b>Summary</b><p>${esc(normalized.summary||"No summary returned.")}</p></section>${sections.map(([name,items])=>`<section><b>${esc(name)}</b><ul>${items.map(item=>`<li>${esc(item)}</li>`).join("")||"<li>None reported.</li>"}</ul></section>`).join("")}</div>`;
}

function rankPdfLinkCandidates(rawText){
  const titleTokens=new Set(String(state.pdf.title||state.pdf.name||"").toLocaleLowerCase().split(/\W+/).filter(token=>token.length>3));
  const page=Number(state.pdf.page);
  const pageTokens=new Set(String(rawText||"").toLocaleLowerCase().split(/\W+/).filter(token=>token.length>5).slice(0,140));
  return allRows().map(({file,record,index})=>{
    let score=0;
    const work=String(record.work||record.document_title||"").toLocaleLowerCase();
    score+=work.split(/\W+/).filter(token=>token.length>3&&titleTokens.has(token)).length*6;
    const start=Number(record.page_start),end=Number(record.page_end??record.page_start);
    if(Number.isFinite(start)&&Number.isFinite(end)&&page>=Math.min(start,end)&&page<=Math.max(start,end))score+=10;
    if(pdfLinks(record).some(link=>link.pdf_file===state.pdf.name))score+=12;
    score+=Math.min(12,String(record.text||"").toLocaleLowerCase().split(/\W+/).filter(token=>token.length>5&&pageTokens.has(token)).slice(0,140).length);
    return {score,candidate:{key:reviewKey(file,index),record_id:record.record_id||"",work:record.work||"",pages:pages(record),citation:record.inline_citation||record.full_citation||"",text:String(record.text||"").slice(0,600)}};
  }).sort((a,b)=>b.score-a.score).slice(0,32).map(item=>item.candidate);
}
async function cleanPdfPageWithLlm(){
  try{
    const raw_text=await currentPdfPageText();if(!raw_text.trim())return toast("No extractable text was found on this page");
    openLlmTaskLauncher({task:"pdf_clean_text",title:"Clean PDF page text",description:`${state.pdf.title||state.pdf.name} · page ${state.pdf.page}`,payload:{mode:"clean_text",raw_text,pdf_file:state.pdf.name||null,pdf_title:state.pdf.title||null,pdf_author:state.pdf.author||null,pdf_page:state.pdf.page,candidates:[]},onForegroundResult:async result=>{state.pdf.text=result.text||"";state.pdf.extractionSource=`LLM cleanup · ${result.model||"model"} · page ${state.pdf.page}`;state.pdf.extractError="";renderPdf(document.querySelector("#main"))}});
  }catch(error){toast(`Could not prepare LLM cleanup: ${error.message}`)}
}
async function draftPdfPageWithLlm(){
  try{
    const raw_text=await currentPdfPageText();if(!raw_text.trim())return toast("No extractable text was found on this page");
    openLlmTaskLauncher({task:"pdf_draft_record",title:"Create draft record from PDF page",description:`${state.pdf.title||state.pdf.name} · page ${state.pdf.page}`,payload:{mode:"draft_record",raw_text,pdf_file:state.pdf.name||null,pdf_title:state.pdf.title||null,pdf_author:state.pdf.author||null,pdf_page:state.pdf.page,candidates:[]},onForegroundResult:async result=>openPdfDraftRecord(result.record||{})});
  }catch(error){toast(`Could not prepare draft generation: ${error.message}`)}
}
async function linkPdfPageWithLlm(){
  if(!state.files.length)return toast("Load JSONL records before asking the LLM to match this PDF page.");
  try{
    const raw_text=await currentPdfPageText(),candidates=rankPdfLinkCandidates(raw_text);
    if(!candidates.length)return toast("No candidate records are loaded");
    openLlmTaskLauncher({task:"pdf_link_record",title:"Link PDF page to record",description:`${state.pdf.title||state.pdf.name} · page ${state.pdf.page} · ${candidates.length} pre-ranked candidates`,payload:{mode:"link_record",raw_text,pdf_file:state.pdf.name||null,pdf_title:state.pdf.title||null,pdf_author:state.pdf.author||null,pdf_page:state.pdf.page,candidates},onForegroundResult:async result=>applyPdfLinkMatch(result.match||{})});
  }catch(error){toast(`Could not prepare LLM record matching: ${error.message}`)}
}


function recordOptionForKey(key){
  const item=lookupRecord(key);
  if(!item)return null;
  return {value:key,label:recordOptionLabel(item.file,item.record,item.index)};
}
function compareSearchIndex(){
  return memoCorpus("compare-search-index",()=>allRows().map(({file,record,index})=>{
    const labelText=recordOptionLabel(file,record,index);
    return {
      value:`${file.id}::${index}`,
      label:labelText,
      search:`${labelText} ${record.document_author||""}`.toLocaleLowerCase(),
    };
  }));
}
function lookupRecord(key){
  if(!key)return null;const [fid,i]=key.split("::");const f=state.files.find(x=>x.id===fid);return f?{file:f,index:+i,record:f.records[+i]}:null;
}
function getCompareLibrary(){
  if(isResearcher()){
    return researcherDbRecords().map(record=>{
      const id=String(record._chroma_id||record.record_id||"");
      const label=`${record.record_id||id} · ${record.work||""}`;
      return {value:id,label,search:`${label} ${record.document_author||""}`.toLocaleLowerCase()};
    });
  }
  return compareSearchIndex();
}
function getCompareRecord(key){
  if(!key)return null;
  if(isResearcher()){
    const record=researcherDbRecords().find(item=>String(item._chroma_id||item.record_id||"")===String(key));
    if(!record)return null;
    const copy={...record};
    delete copy._chroma_id;
    delete copy._researcher_text_policy;
    return {record:copy,label:`${record.record_id||key} · ${record.work||""}`};
  }
  const item=lookupRecord(key);
  if(!item?.record)return null;
  return {record:item.record,label:recordOptionLabel(item.file,item.record,item.index)};
}
async function ensureCompareLibrary(){
  if(!isResearcher())return getCompareLibrary();
  if(!state.activeStore){
    try{await refreshStores()}catch{ /* stores may be unavailable */ }
  }
  if(!state.storeRecords.length&&state.activeStore){
    state.storePageSize=Math.max(Number(state.storePageSize||50),100);
    try{await loadStorePage()}catch{ /* page load is best-effort for Compare */ }
  }
  return getCompareLibrary();
}

const HTTP_ERROR_STORAGE_KEY="derridai.httpErrors.v1";
function storeHttpError(entry){
  try{
    const current=JSON.parse(localStorage.getItem(HTTP_ERROR_STORAGE_KEY)||"[]");
    const rows=Array.isArray(current)?current:[];
    rows.unshift(entry);
    localStorage.setItem(HTTP_ERROR_STORAGE_KEY,JSON.stringify(rows.slice(0,50)));
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  }catch{}
}
async function api(path,options={}){
  const method=String(options.method||"GET").toUpperCase();
  let response;
  try{
    response=await fetch(path,{headers:{"Content-Type":"application/json",...(options.headers||{})},...options});
  }catch(error){
    const diagnostic=String(error?.message||error);
    const wrapped=new Error(`Network error · ${diagnostic}`);
    wrapped.diagnostic=diagnostic;
    wrapped.status=0;
    wrapped.fullMessage=wrapped.message;
    wrapped.requestPath=String(path);
    storeHttpError({timestamp:new Date().toISOString(),method,path:String(path),status:0,statusText:"Network error",message:wrapped.message,diagnostic,responseBody:""});
    throw wrapped;
  }
  if(response.status===401&&!String(path).startsWith("/api/auth/"))window.dispatchEvent(new CustomEvent("derridai-auth-expired"));
  const text=await response.text();
  let payload={};
  try{payload=text?JSON.parse(text):{}}catch{payload={detail:text}}
  if(!response.ok){
    const detail=fullHttpErrorDetail(payload,text,response.statusText);
    const diagnostic=typeof payload?.detail==="object"&&!Array.isArray(payload.detail)?String(payload.detail?.diagnostic||""):"";
    const message=`HTTP ${response.status}${response.statusText?` ${response.statusText}`:""} · ${detail}`;
    const error=new Error(message);
    error.status=response.status;
    error.statusText=response.statusText;
    error.diagnostic=diagnostic;
    error.payload=payload;
    error.responseBody=text;
    error.requestPath=String(path);
    error.requestMethod=method;
    error.fullMessage=message;
    storeHttpError({timestamp:new Date().toISOString(),method,path:String(path),status:response.status,statusText:response.statusText||"",message,diagnostic,responseBody:text});
    throw error;
  }
  return payload;
}
async function refreshStores(){
  const data=await api("/api/stores");
  state.stores=data.stores||[];
  state.storesLastFetchedAt=Date.now();
  const corpus=recordStores();
  if(state.activeStore&&!corpus.some(store=>store.name===state.activeStore))state.activeStore="";
  if(!state.activeStore&&corpus.length)state.activeStore=corpus[0].name;
  return state.stores;
}
async function refreshStoreWorks(force=false){
  if(!state.activeStore){
    state.storeWorks=[];
    state.storeWorkStats=[];
    state.storeWorksStore="";
    state.storeWork="";
    return;
  }
  if(!force&&state.storeWorksStore===state.activeStore)return;
  const data=await api(`/api/stores/${encodeURIComponent(state.activeStore)}/works`);
  state.storeWorks=data.works||[];
  state.storeWorkStats=data.stats||state.storeWorks.map(work=>({work,count:null}));
  state.storeWorksStore=state.activeStore;
  if(state.storeWork&&!state.storeWorks.includes(state.storeWork))state.storeWork="";
}
async function loadStorePage(){
  if(!state.activeStore){state.storeRecords=[];state.storeCount=0;return}
  const offset=Math.max(0,(state.storePage-1)*state.storePageSize);
  const params=new URLSearchParams({limit:String(state.storePageSize),offset:String(offset)});
  if(state.storeWork)params.set("work",state.storeWork);
  if(state.storeSort?.key){
    params.set("sort_field",state.storeSort.key);
    params.set("sort_dir",state.storeSort.dir===-1?"desc":"asc");
  }
  const activeFilters=Object.fromEntries(Object.entries(state.storeFilters||{}).filter(([,value])=>String(value||"").trim()));
  if(Object.keys(activeFilters).length)params.set("filters",JSON.stringify(activeFilters));
  const data=await api(`/api/stores/${encodeURIComponent(state.activeStore)}/records?${params}`);
  state.storeRecords=data.records||[];
  state.storeCount=data.count||0;
  const maxPage=Math.max(1,Math.ceil(state.storeCount/state.storePageSize));
  if(state.storePage>maxPage){state.storePage=maxPage;return loadStorePage()}
}
async function exportStoreJsonl({store=state.activeStore,work=null,downloadFile=false,loadTab=false}={}){
  if(!store)return toast("Select a Chroma collection first");
  const params=new URLSearchParams();
  if(work)params.set("work",work);
  const op=showOperationProgress(`Exporting ${store}`,1);
  try{
    updateOperationProgress(op,0,1,work?`Reading work: ${work}`:"Reading complete collection…");
    const payload=await api(`/api/stores/${encodeURIComponent(store)}/export${params.toString()?`?${params}`:""}`);
    const records=payload.records||[];
    const suffix=work?`-${String(work).replace(/[^a-z0-9]+/gi,"-").replace(/^-|-$/g,"")}`:"";
    const name=`${store}${suffix}.jsonl`;
    const jsonl=records.map(record=>JSON.stringify(record)).join("\n")+(records.length?"\n":"");
    if(downloadFile)download(name,jsonl);
    if(loadTab){
      const file={
        id:uid(),
        name,
        records:records.map(record=>cloneAuditValue(record)),
        errors:[],
        dirty:new Set(),
        imported_at:new Date().toISOString(),
        imported_from_chroma:store,
      };
      state.files.push(file);
      await persistFileNow(file);
      state.activeFileId=file.id;
      persistPrefs();
      navigateTo("list",{fileId:file.id});
    }
    updateOperationProgress(op,1,1,`${records.length.toLocaleString()} records exported`);
    setTimeout(()=>hideOperationProgress(op),600);
    if(!loadTab)toast(`Exported ${records.length.toLocaleString()} records from ${store}`);
    return records;
  }catch(error){
    updateOperationProgress(op,0,1,`Failed: ${error.message}`);
    setTimeout(()=>hideOperationProgress(op),1800);
    toast(`Chroma export failed: ${error.message}`);
    return null;
  }
}
const vectorCollectionBridge=createVectorCollectionBridge({
  state,workIndex,recordStores,tr,trf,esc,icon,api,refreshStores,persistPrefs,
  upsertRows,toast,openMessageModal,decorateDisabledControls,showAppModal,
});
function notifyVectorStoresChanged(){return vectorCollectionBridge.notifyVectorStoresChanged()}
function openDatabaseCreationFromResearch(){return vectorCollectionBridge.openDatabaseCreationFromResearch()}
function openCollectionCreationWizard(options={}){return vectorCollectionBridge.openCollectionCreationWizard(options)}

const HIGH_RISK_TOUCHUP_FIELDS = new Set(["text","record_id","canonical_work_id","inline_citation","full_citation","edition","year","page_start","page_end"]);









function normalizeTouchupItems(inputItems=null){
  const fallback=(()=>{
    const file=activeFile(),record=selectedRecord();
    if(!file||!record)return [];
    const index=selectedIndex(file);
    return [{file,index,record,key:reviewKey(file,index)}];
  })();
  return (inputItems?.length?inputItems:fallback).map(item=>({
    ...item,
    record:item.file.records[item.index],
    key:item.key||reviewKey(item.file,item.index),
  })).filter(item=>item.record);
}
function touchupWorkspaceInfo(inputItems=null,initialMode="foreground"){
  const items=normalizeTouchupItems(inputItems);
  const availableFields=[];
  for(const item of items){
    for(const field of touchupFieldsForRecord(item.record))if(!availableFields.includes(field)&&field!=="updates")availableFields.push(field);
  }
  const attributionPreset=["speaker","position_holder","target","is_direct_quote","quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent","quotation_chain"].filter(field=>availableFields.includes(field));
  const semanticPreset=["discourse_role","proposition_status","semantic_function","stance","claim_scope","topics","concepts","persons","works_referenced"].filter(field=>availableFields.includes(field));
  const preset=state.appConfig.default_review_preset;
  return {
    items,
    initialMode,
    availableFields,
    attributionPreset,
    semanticPreset,
    defaultSelection:preset==="text"&&availableFields.includes("text")?["text"]:preset==="semantic"?semanticPreset:attributionPreset,
    groups:TOUCHUP_GROUPS,
    highRiskFields:[...HIGH_RISK_TOUCHUP_FIELDS],
    fieldLabels:Object.fromEntries(availableFields.map(field=>[field,label(field)])),
    profiles:providerProfiles().map(profile=>({...profile,api_key:undefined})),
    providerProfileId:state.appConfig.review_provider_profile||state.appConfig.default_provider_profile||defaultProviderProfile()?.id||"",
    defaultMode:initialMode==="auto"?"auto":state.appConfig.default_llm_run_mode==="foreground"?"foreground":"background",
  };
}
async function touchupProviderStatus(profileId){
  const profile=providerProfile(profileId);
  if(!profile)return {provider:"ollama",available:false,models:[],configured_model:"",error:"No provider profile configured"};
  try{
    const status=await api("/api/llm/status",{method:"POST",body:JSON.stringify({provider:profile.type,base_url:profile.base_url||null,api_key:profile.type==="openai"?(profile.api_key||""):null})});
    state.providerStatuses[profile.id]=status;
    return status;
  }catch(error){return {provider:profile.type,available:false,models:[],configured_model:profile.model||"",error:error.message};}
}
function touchupRequestConfig(profileId,model,fields=[]){
  const profile=providerProfile(profileId);
  const config=providerRequestConfig(profile,{textReview:fields.includes("text")});
  if(config&&model)config.model=model;
  return config;
}
async function touchupRequest(item,fields,config,instructions=""){
  return api("/api/llm/touchup",{method:"POST",body:JSON.stringify({
    record:touchupRecordPayload(item.file.records[item.index],fields),fields,instructions,
    model:config.model,provider:config.provider,base_url:config.base_url,api_key:config.api_key,ollama:config.ollama,
  })});
}
async function touchupSubmitBackground(items,config,fields,instructions,mode){
  return submitBackgroundLlmJob(items,config,fields,instructions,mode);
}
function touchupApplyResults(items,results,approvals,all=false,reviewOnly=false){
  const batchId=uid();let appliedFields=0,reviewedRecords=0;
  for(const item of items){
    const result=results[item.key];if(!result?.proposal)continue;
    const fields=reviewOnly?[]:(all?Object.keys(result.proposal.changes||{}):[...(approvals[item.key]||[])]);
    const changes={};
    for(const field of fields)if(field in result.proposal.changes)changes[field]=result.proposal.changes[field];
    const record=item.file.records[item.index];
    if(record.needs_review===true)changes.needs_review=false;
    if(record.review_reason!==undefined&&record.review_reason!==null&&record.review_reason!=="")changes.review_reason=null;
    appliedFields+=applyRecordChanges(item.file,item.index,changes,{source:"llm_review",model:result.proposal.model,batchId,rationale:result.proposal.rationale});
    reviewedRecords++;
  }
  clearReviewSelection();shell();renderView();
  toast(`Marked ${reviewedRecords} record${reviewedRecords===1?"":"s"} reviewed · ${appliedFields} tracked field change${appliedFields===1?"":"s"}`);
  return {appliedFields,reviewedRecords};
}


async function syncResearcherProviderProfiles(){
  const approved=providerProfiles().filter(profile=>profile.researcher_enabled).map(profile=>({...profile}));
  const result=await api("/api/system/researcher-providers",{method:"PUT",body:JSON.stringify({profiles:approved})});
  state.researcherProviderProfiles=result.profiles||[];
}

async function checkHealth(){
  try{
    state.health=await api("/api/health");
    ensureProviderProfiles();
    await refreshProviderStatuses();
  }catch(error){
    state.health={ok:false,error:error.message};
    state.providerStatuses={};
    state.llmStatus={
      provider:defaultProviderProfile()?.type||"ollama",
      available:false,
      models:[],
      error:error.message,
    };
  }
  updateSystemCard();
  if(state.health?.chroma?.available){
    try{
      await refreshStores();
      if(isResearcher()&&state.activeStore)await refreshStoreWorks(true);
      persistPrefs();
      const active=document.activeElement;
      const userIsEditing=active&&active!==document.body&&["INPUT","TEXTAREA","SELECT"].includes(active.tagName);
      if(!userIsEditing){shell();renderView()}
    }catch(error){console.warn("Initial Chroma collection refresh failed",error)}
  }
}




function translatedNavLabel(item){
  const keys={home:"nav.dashboard",list:"nav.records",record:"nav.record",works:"nav.works",global:"nav.search",annotations:"nav.annotations",pdf:"nav.pdf",compare:"nav.compare",vector:"nav.vector",rag:"nav.rag",faq:"nav.faq",responsecache:"nav.cache",providers:"nav.providers",config:"nav.config"};
  return keys[item.id]?tr(keys[item.id],item.label):item.label;
}
function translatedSectionLabel(section){
  const keys={Overview:"section.overview",Corpus:"section.corpus",Research:"section.research",Tools:"section.tools",System:"section.system"};
  return keys[section]?tr(keys[section],section):section;
}
function getShellSnapshot(){
  const ctx=currentContext();
  const totalLoaded=allRows().length;
  const flagged=needsReviewItems().length;
  const pending=state.activeStore?pendingUpsertRows().length:0;
  const corpusStores=recordStores();
  const dbRecords=corpusStores.reduce((sum,store)=>sum+(Number(store.count)||0),0);
  const cacheCount=Number(responseCacheStore()?.count||0);
  const activeJobs=state.jobs.filter(job=>["queued","running","cancelling"].includes(job.status)).length;
  return {
    view:state.view,
    sidebarCollapsed:state.sidebarCollapsed,
    files:state.files.map(file=>describeRecordsFile(file,state.activeFileId)),
    context:ctx,
    totalLoaded,
    flagged,
    pending,
    activeJobs,
    corpusStoreCount:corpusStores.length,
    dbRecords,
    cacheCount,
    hasCorpusDb:hasCorpusDb(),
    dbUnavailableReason:dbUnavailableReason(),
    activeStore:state.activeStore,
    canEdit:canUse("editLocalRecords")&&state.view==="record"&&Boolean(selectedRecord()),
    canGoBack:state.navHistory.length>0,
    canGoForward:state.navForward.length>0,
    backLabel:state.navHistory.length?viewLabel(state.navHistory[state.navHistory.length-1].view):"",
    forwardLabel:state.navForward.length?viewLabel(state.navForward[state.navForward.length-1].view):"",
    selectedEvidenceCount:selectedEvidenceEntries().length,
    systemHtml:systemCardHtml(),
    nav:getNavItems(),
  };
}
// Navigation membership depends only on the signed-in user, the static view list,
// and translations, never on workspace/bootstrap state. The Vue shell calls this as
// soon as a user exists so the menu is complete before the slow runtime bootstrap.
function getNavItems(){
  return viewConfig.filter(item=>canAccessPage(item.id)).map(item=>({
    ...item,
    label:item.id==="home"?tr("nav.home","Home"):(isResearcher()&&item.id==="vector"?tr("research.corpus_search","Corpus search"):translatedNavLabel(item)),
    section:translatedSectionLabel(item.section),
    disabledReason:viewDisabledReason(item.id),
  }));
}

function toggleSidebar(){
  state.sidebarCollapsed=!state.sidebarCollapsed;
  persistPrefs();
  shell();
}
function activateFile(fileId){
  if(["list","record"].includes(state.view)){
    state.activeFileId=fileId;
    persistPrefs();
    syncUrl({replace:true});
    shell();
    renderView();
  }else navigateTo("list",{fileId});
}
function triggerImport(fileList){return canUse("manageCorpus")?importFiles(fileList):toast("Your role does not have permission to load corpus files.")}
function triggerMerge(){return canUse("manageCorpus")?openMergeDialog():toast("Your role does not have permission to merge corpus files.")}
function triggerSubset(){return canUse("manageCorpus")?openSubsetBuilder():toast("Your role does not have permission to create subsets.")}
function triggerBulkEdit(){return canUse("editLocalRecords")?openBulkFieldEditor():toast("Your role does not have permission to edit records.")}
function triggerOcrClean(){return canUse("editLocalRecords")?openOcrCleanupDialog():toast("Your role does not have permission to edit records.")}
function triggerReviewFlagged(){return canUse("editLocalRecords")?openTouchup(needsReviewItems()):toast("Your role does not have permission to review records.")}
function triggerAutoImproveFlagged(){return canUse("editLocalRecords")?openTouchup(needsReviewItems(),"auto"):toast("Your role does not have permission to modify records.")}
function triggerUpsertQueue(){return canUse("manageCorpus")?openUpsertQueue():toast("Your role does not have permission to manage corpus databases.")}
function triggerOperations(){return navigateTo("home")}
function triggerExport(){return canUse("manageCorpus")?exportMenu():toast("Your role does not have permission to export corpus data.")}
function triggerEdit(){return canUse("editLocalRecords")?openEditor():toast("Your role does not have permission to edit records.")}
function triggerBack(){return goBack()}
function triggerForward(){return goForward()}
/**
 * Navigate the runtime and, when supplied, preserve an explicit native URL.
 * @param {string} view
 * @param {string} [href=""]
 */
function navigateView(view,href=""){return navigateTo(view,{href})}
function closeWorkspaceFile(fileId){return closeFile(fileId)}
function notifyToast(message,options={}){return toast(message,options)}

let chartTooltip=null;
function ensureChartTooltip(){
  if(chartTooltip?.isConnected)return chartTooltip;
  chartTooltip=document.createElement("div");chartTooltip.className="chart-hover-tooltip";document.body.appendChild(chartTooltip);return chartTooltip;
}
document.addEventListener("pointermove",event=>{
  const target=event.target.closest?.("[data-chart-tip]");
  if(!target){if(chartTooltip)chartTooltip.classList.remove("show");return}
  const tip=ensureChartTooltip();tip.textContent=target.dataset.chartTip||"";tip.style.left=`${Math.min(window.innerWidth-280,event.clientX+14)}px`;tip.style.top=`${Math.max(8,event.clientY+14)}px`;tip.classList.add("show");
});

window.addEventListener("dragover",e=>e.preventDefault());
window.addEventListener("drop",e=>{if(e.dataTransfer?.files?.length){e.preventDefault();if(!isResearcher())importFiles([...e.dataTransfer.files].filter(f=>/\.(jsonl|ndjson|json)$/i.test(f.name)));}});
document.addEventListener("click",event=>{
  const resultButton=event.target.closest?.("[data-toast-open-result],[data-job-result],[data-rag-job-result],[data-recent-rag-result]");
  if(!resultButton)return;
  const jobId=resultButton.dataset.toastOpenResult||resultButton.dataset.jobResult||resultButton.dataset.ragJobResult||resultButton.dataset.recentRagResult;
  if(!jobId)return;
  event.preventDefault();
  event.stopImmediatePropagation();
  resultButton.disabled=true;
  const original=resultButton.innerHTML;
  resultButton.textContent="Opening…";
  void openJobResults(jobId).catch(error=>openMessageModal({title:"Could not open operation result",message:error.message||String(error),tone:"danger"})).finally(()=>{if(resultButton.isConnected){resultButton.disabled=false;resultButton.innerHTML=original}});
},{capture:true});

document.addEventListener("click",event=>{
  const loadedButton=event.target.closest("[data-copy-row-key]");
  if(loadedButton){
    event.stopPropagation();
    const item=reviewItemFromKey(loadedButton.dataset.copyRowKey);
    if(item)copyJsonToClipboard(item.file.records[item.index],item.record.record_id||"record");
    else toast("The source record is no longer loaded");
    return;
  }
  const citeButton=event.target.closest("[data-cite-row-key]");
  if(citeButton){
    event.stopPropagation();
    const item=reviewItemFromKey(citeButton.dataset.citeRowKey);
    if(item)copyCitation(item.record,citeButton.dataset.citeKind||"inline");
    return;
  }
  const dbCite=event.target.closest("[data-admin-db-cite],[data-r-cite]");
  if(dbCite){
    event.preventDefault();event.stopPropagation();
    const id=String(dbCite.dataset.adminDbId||dbCite.dataset.rId||"");
    const result=(state.storeSearchResults||[]).find(item=>String(item.id||item.record?._chroma_id||item.record?.record_id||"")===id);
    const record=result?.record||(state.storeRecords||[]).find(item=>String(item._chroma_id||item.record_id||"")===id);
    if(record)copyCitation(record,dbCite.dataset.adminDbCite||dbCite.dataset.rCite||"inline");
    else toast("Citation source is no longer available",{tone:"warn"});
    return;
  }
  const evidenceButton=event.target.closest("[data-toggle-workspace-evidence]");
  if(evidenceButton){
    event.stopPropagation();
    const item=reviewItemFromKey(evidenceButton.dataset.toggleWorkspaceEvidence);
    if(item){toggleWorkspaceEvidence(item.file,item.index);renderView()}
    return;
  }
  const storeButton=event.target.closest("[data-copy-store-record]");
  if(storeButton){
    event.stopPropagation();
    const record=state.storeRecords.find(item=>String(item._chroma_id||"")===String(storeButton.dataset.copyStoreRecord||""));
    if(record){const copy={...record};delete copy._chroma_id;copyJsonToClipboard(copy,copy.record_id||"Chroma record")}
  }
});
let researcherPolicy={ready:false,blocked:new Set(),contextual:[]};
let researcherPolicyToastAt=0;
const researcherLeet={"0":"o","1":"i","3":"e","4":"a","5":"s","7":"t","@":"a","$":"s"};
function normalizeResearcherToken(value){
  const text=String(value||"").normalize("NFKC").replace(/[013457@$]/g,ch=>researcherLeet[ch]||ch).toLocaleLowerCase();
  return text.replace(/(?<=\w)[._*~-]+(?=\w)/g,"");
}
async function researcherTokenDigest(value){
  if(!globalThis.crypto?.subtle)return "";
  const buf=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(normalizeResearcherToken(value)));
  return Array.from(new Uint8Array(buf),b=>b.toString(16).padStart(2,"0")).join("");
}
async function refreshResearcherContentPolicy(){
  if(!state.userContext){researcherPolicy={ready:false,blocked:new Set(),contextual:[]};return}
  try{
    const data=await api("/api/i18n/content-policy");
    researcherPolicy={
      ready:Boolean(data?.ready),
      blocked:new Set(Array.isArray(data?.blocked_term_hashes)?data.blocked_term_hashes:[]),
      contextual:Array.isArray(data?.contextual)?data.contextual:[],
    };
  }catch{
    researcherPolicy={ready:false,blocked:new Set(),contextual:[]};
  }
}
async function filterResearcherInputElement(target){
  if(!isResearcher()||!(target instanceof HTMLElement)||!researcherPolicy.ready)return;
  const acceptsText=target instanceof HTMLTextAreaElement||(target instanceof HTMLInputElement&&["text","search","url","email","tel"].includes(target.type))||target.isContentEditable;
  if(!acceptsText)return;
  const original=target.isContentEditable?target.textContent||"":target.value||"";
  const words=[...original.matchAll(/[\w'’]+/g)];
  const remove=[];
  for(const match of words){
    const raw=match[0];
    const digest=await researcherTokenDigest(raw);
    if(!digest)continue;
    if(researcherPolicy.blocked.has(digest)){remove.push(raw);continue}
    const rule=researcherPolicy.contextual.find(item=>item.term_hash===digest);
    if(!rule)continue;
    if(rule.allow_title_case&&raw===raw.charAt(0).toUpperCase()+raw.slice(1).toLowerCase()&&raw!==raw.toLowerCase())continue;
    const index=words.indexOf(match);
    const surrounding=words.slice(Math.max(0,index-3),index+4).map(item=>normalizeResearcherToken(item[0])).join(" ");
    if((rule.allow_if_surrounding||[]).some(marker=>surrounding.includes(normalizeResearcherToken(marker))))continue;
    const before=normalizeResearcherToken(original.slice(Math.max(0,match.index-20),match.index));
    if((rule.allow_if_before_markers||[]).some(marker=>before.includes(normalizeResearcherToken(marker))))continue;
    remove.push(raw);
  }
  if(!remove.length)return;
  let filtered=original;
  for(const token of remove)filtered=filtered.replace(new RegExp(`\\b${token.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")}\\b`),"");
  filtered=filtered.replace(/ {2,}/g," ");
  if(target.isContentEditable)target.textContent=filtered;else target.value=filtered;
  target.dispatchEvent(new Event("change",{bubbles:true}));
  const now=Date.now();if(now-researcherPolicyToastAt>1200){researcherPolicyToastAt=now;toast(tr("content_filter.warning","That language is not permitted for researcher accounts. The flagged term was removed."),{tone:"warn"})}
}
document.addEventListener("input",event=>{void filterResearcherInputElement(event.target)},true);

window.addEventListener("popstate",()=>{
  applyUrlState();
  persistPrefs();
  shell();
  renderView();
});

let metadataSearchDelegationWired=false;
function wireMetadataSearchDelegation(){if(metadataSearchDelegationWired)return;metadataSearchDelegationWired=true;document.addEventListener("click",event=>{const button=event.target instanceof Element?event.target.closest("[data-meta-search-field][data-meta-search-value]"):null;if(!button)return;if(button.closest("#main")){event.preventDefault();event.stopPropagation();searchByMetadata(button.dataset.metaSearchField,button.dataset.metaSearchValue,{contains:button.dataset.metaSearchContains==="true"})}},true)}
let tabScrollPreservationWired=false;
function wireTabScrollPreservation(){
  if(tabScrollPreservationWired)return;
  tabScrollPreservationWired=true;
  const selector=['[role="tab"]','.view-tab','.db-browser-tab','.search-mode-tabs button','.dashboard-search-tabs button','.annotation-tabs button','.annotations-tabs button','.record-view-tabs button','.compare-tabs button','.config-tabs button'].join(',');
  const arm=target=>{
    if(!target)return;
    const top=window.scrollY,left=window.scrollX,main=document.querySelector('#main');
    let cancelled=false,quietTimer=null,stopTimer=null,observer=null;
    const restore=()=>{if(cancelled)return;if(Math.abs(window.scrollY-top)>1||Math.abs(window.scrollX-left)>1)window.scrollTo({top,left,behavior:'auto'})};
    const stop=()=>{observer?.disconnect();if(quietTimer)clearTimeout(quietTimer);if(stopTimer)clearTimeout(stopTimer);window.removeEventListener('wheel',cancel);window.removeEventListener('touchmove',cancel)};
    const cancel=()=>{cancelled=true;stop()};
    observer=main?new MutationObserver(()=>{restore();if(quietTimer)clearTimeout(quietTimer);quietTimer=setTimeout(stop,140)}):null;
    observer?.observe(main,{childList:true,subtree:true});
    window.addEventListener('wheel',cancel,{passive:true,once:true});window.addEventListener('touchmove',cancel,{passive:true,once:true});
    requestAnimationFrame(restore);stopTimer=setTimeout(stop,1200);
  };
  document.addEventListener('pointerdown',event=>{const target=event.target instanceof Element?event.target.closest(selector):null;if(target)arm(target)},true);
  document.addEventListener('keydown',event=>{if(!['Enter',' '].includes(event.key))return;const target=event.target instanceof Element?event.target.closest(selector):null;if(target)arm(target)},true);
}

async function bootstrapRuntime(){
  wireTabScrollPreservation();wireMetadataSearchDelegation();
  await restoreWorkspace();
  try{
    if(!state.appConfig.ui_color_scheme)state.appConfig.ui_color_scheme=localStorage.getItem("derridai.ui.scheme")||"system";
    if(!state.appConfig.ui_contrast)state.appConfig.ui_contrast=localStorage.getItem("derridai.ui.contrast")||"system";
  }catch{ /* localStorage can be blocked */ }
  applyAppearance({
    ui_color_theme:state.appConfig.ui_color_theme,
    ui_color_scheme:state.appConfig.ui_color_scheme||"system",
    ui_contrast:state.appConfig.ui_contrast||"system",
  });
  try{
    const providerData=await api("/api/system/researcher-providers");
    state.researcherProviderProfiles=Array.isArray(providerData.profiles)?providerData.profiles:[];
  }catch(error){
    console.warn("Could not load researcher provider profiles",error);
    state.researcherProviderProfiles=[];
  }
  if(isResearcher()){
    state.files=[];
    state.activeFileId=null;
    state.selected={};
    state.reviewSelection=new Set();
    if(!["home","rag","vector","works","global","record","compare","annotations","config"].includes(state.view))state.view="home";
  }
  applyUrlState();
  if(!canAccessPage(state.view))state.view="home";
  shell();
  // A native Vue route may be active without #main. In that case bootstrap
  // background health/job state only; RuntimeSurface will render when mounted.
  if(document.querySelector("#main"))renderView();
  await checkHealth();
  // One discovery request on startup is not a polling loop. Polling begins only
  // if this request finds an active job and then runs every four seconds.
  await refreshJobs({rerender:false});
  if(state.view==="home"&&document.querySelector("#main"))renderDashboard(document.querySelector("#main"));
  startJobPolling();
  if(!isResearcher()&&state.appConfig.warm_default_provider_on_start===true)warmupConfiguredLlm();
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
  pauseRuntime,
  viewPathMap,
  pathViewMap,
  bootstrapRuntime,
  renderView,
  navigateView,
  toggleSidebar,
  activateFile,
  closeWorkspaceFile,
  triggerImport,
  triggerMerge,
  triggerSubset,
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
  triggerOperations,
  triggerExport,
  triggerEdit,
  triggerBack,
  triggerForward,
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
  syncResearcherProviderProfiles,
  notifyToast,
  registerExternalJob,
  dbUnavailableReason,
  hasCorpusDb,
  openDatabaseCreationFromResearch,
  notifyVectorStoresChanged,
  openCollectionCreationWizard,
  upsertRows,
  exportStoreJsonl,
  persistPrefs,
  lookupRecord,
  getCompareLibrary,
  getCompareRecord,
  ensureCompareLibrary,
  copyJsonToClipboard,
  copyCitation,
  flushWorkspacePrefs,
  applyUiTheme,
  applyAppearance,
  downloadFullBackup,
  restoreFullBackup,
  clearAllUpdates,
  deleteAllDerridaiBrowserState,
  backupContainsCredentials,
  pendingUpsertRows,
  decorateDisabledControls,
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
  recordWorkspaceNavigate,
  setRecordWorkspaceFind,
  toggleCurrentRecordEvidence,
  toggleCurrentRecordReviewSelection,
  copyCurrentRecordCitation,
  copyCurrentRecordJson,
  saveCurrentRecordChanges,
  addCurrentRecordAnnotation,
  removeCurrentRecordAnnotation,
  currentRecordPrimaryAction,
  searchCurrentRecordMetadata,
  navigateRecordWorkspace,
  getWorksWorkspaceSnapshot,
  setWorksSearch,
  setWorksOverview,
  setWorksStore,
  syncWork,
  syncAllWorks,
  searchWork,
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
  recordsListMetadataSearch,
  setRecordsListColumns,
  resetRecordsListColumns,
  getRecordsListShareHref,
  recordsListCommand,
};
