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
import { countOccurrences, flattenValueList, parseJsonl, valueMatches } from "../domain/recordQuery";
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
import { createPdfExplorerRenderer } from "../domain/pdfExplorerRenderer";
import { createJobDialogs } from "../domain/jobDialogs";
import { createWorkDialogs } from "../domain/workDialogs";
import { createRecordDialogs } from "../domain/recordDialogs";
import { createOperationDock } from "../domain/operationDock";
import { createModalDialogs } from "../domain/modalDialogs";
import { createNavigation } from "../domain/navigation";
import { pathViewMap, viewPathMap } from "../domain/navigation";
import { createWorkspacePersistence } from "../domain/workspacePersistence";
import { createEvidenceSelection } from "../domain/evidenceSelection";
import { createRecordEditing } from "../domain/recordEditing";
import { createDbPresenceUpsert } from "../domain/dbPresenceUpsert";
import { createOperationsPanelBridge } from "../domain/operationsPanelBridge";
import { createPdfLinking } from "../domain/pdfLinking";
import { createAppLifecycle } from "../domain/appLifecycle";
import { createCompareLibrary } from "../domain/compareLibrary";
import { createBackupWorkspace } from "../domain/backupWorkspace";
import { createResearchWorkspace } from "../domain/researchWorkspace";
import { createAnnotationsWorkspace } from "../domain/annotationsWorkspace";
import { subscribeToJobChanges, touchJobs } from "../state/jobsState";
import { touchCorpus } from "../state/workspaceState";
import { createRuntimeState } from "./runtimeState";
import { createVectorCollectionBridge } from "./vectorCollectionBridge";
import { relativeTimeLabel } from "../domain/relativeTimeLabel";
import { createRecordSubsets } from "../domain/recordSubsets";

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
  tr,label,display,pages,recordFields,uid:()=>uid(),dbSearchWhere,filterOpsForField,
  recordDbStatus:(...args)=>recordDbStatus(...args),
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
  tr,trf,pages,label,display,
  recordDbStatus:(...args)=>recordDbStatus(...args),
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
  state,api,isResearcher,
  persistPrefs:(...args)=>persistPrefs(...args),
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
const {compareSearchIndex,lookupRecord,getCompareLibrary,getCompareRecord,ensureCompareLibrary}=createCompareLibrary({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allRows:(...args)=>allRows(...args),
  isResearcher:(...args)=>isResearcher(...args),
  loadStorePage:(...args)=>loadStorePage(...args),
  memoCorpus:(...args)=>memoCorpus(...args),
  recordOptionLabel:(...args)=>recordOptionLabel(...args),
  refreshStores:(...args)=>refreshStores(...args),
  researcherDbRecords:(...args)=>researcherDbRecords(...args),
});
const {warmupProviderProfile,warmupConfiguredLlm,importFiles,closeFile,checkHealth}=createAppLifecycle({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api:(...args)=>api(...args),
  applyCompressedTableUrlState:(...args)=>applyCompressedTableUrlState(...args),
  clearFileDerivedState:(...args)=>clearFileDerivedState(...args),
  decompressUrlState:(...args)=>decompressUrlState(...args),
  defaultProviderProfile:(...args)=>defaultProviderProfile(...args),
  ensureProviderProfiles:(...args)=>ensureProviderProfiles(...args),
  idbDelete:(...args)=>idbDelete(...args),
  invalidateCorpusCache:(...args)=>invalidateCorpusCache(...args),
  isResearcher:(...args)=>isResearcher(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  parseJsonl:(...args)=>parseJsonl(...args),
  persistFileNow:(...args)=>persistFileNow(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  providerDisplayName:(...args)=>providerDisplayName(...args),
  providerProfile:(...args)=>providerProfile(...args),
  providerRequestConfig:(...args)=>providerRequestConfig(...args),
  refreshProviderStatuses:(...args)=>refreshProviderStatuses(...args),
  refreshStoreWorks:(...args)=>refreshStoreWorks(...args),
  refreshStores:(...args)=>refreshStores(...args),
  renderDashboard:(...args)=>renderDashboard(...args),
  renderView:(...args)=>renderView(...args),
  shell:(...args)=>shell(...args),
  stableJsonlFileIdentity:(...args)=>stableJsonlFileIdentity(...args),
  syncUrl:(...args)=>syncUrl(...args),
  toast:(...args)=>toast(...args),
  updateSystemCard:(...args)=>updateSystemCard(...args),
});
const {pdfDisplayTitle,loadedPdfPagesForRecord,allLinkedRowsForLoadedPdf,loadPdfMetadata,openPdfExplorerWorkspace,openLoadedPdfPage,linkedPdfRows,linkPdfPage,unlinkPdfLink,unlinkAllPdfLinks}=createPdfLinking({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allRows:(...args)=>allRows(...args),
  applyRecordChanges:(...args)=>applyRecordChanges(...args),
  normalizePdfLinkChanges:(...args)=>normalizePdfLinkChanges(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  pdfLinks:(...args)=>pdfLinks(...args),
  renderPdf:(...args)=>renderPdf(...args),
  renderView:(...args)=>renderView(...args),
  shell:(...args)=>shell(...args),
  toast:(...args)=>toast(...args),
});
const {notifyOperationsChanged,operationsBridge,renderOperationsPanel,mountOperationsPanelHost,refreshOperationsPanelOnly,wireCorpusBuildsHomeCard,refreshCorpusBuildsHomeCardOnly,gradeRagResponse,removeRagJob,clearFinishedRagJobs,ragProgressPanelHtml,wireRagProgressPanel,refreshRagProgressPanel,renderCorpusBuildsHomeCard}=createOperationsPanelBridge({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  api:(...args)=>api(...args),
  cancelBackgroundJob:(...args)=>cancelBackgroundJob(...args),
  formatTimestamp:(...args)=>formatTimestamp(...args),
  humanDuration:(...args)=>humanDuration(...args),
  isResearcher:(...args)=>isResearcher(...args),
  jobElapsedSeconds:(...args)=>jobElapsedSeconds(...args),
  openJobDetails:(...args)=>openJobDetails(...args),
  openJobResults:(...args)=>openJobResults(...args),
  openLlmTaskLauncher:(...args)=>openLlmTaskLauncher(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  operationViewModel:(...args)=>operationViewModel(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  pruneClientJobState:(...args)=>pruneClientJobState(...args),
  ragGradeEvidencePayload:(...args)=>ragGradeEvidencePayload(...args),
  ragGradeHtml:(...args)=>ragGradeHtml(...args),
  refreshJobs:(...args)=>refreshJobs(...args),
  showAppModal:(...args)=>showAppModal(...args),
  toast:(...args)=>toast(...args),
  tr:(...args)=>tr(...args),
});
const {applyRecordChanges,clearRecordUpdates,clearAllUpdates,historyVersionChanges,restoreRecordHistoryVersion}=createRecordEditing({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allRows:(...args)=>allRows(...args),
  cloneAuditValue:(...args)=>cloneAuditValue(...args),
  invalidateCorpusCache:(...args)=>invalidateCorpusCache(...args),
  label:(...args)=>label(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  persistFile:(...args)=>persistFile(...args),
  renderView:(...args)=>renderView(...args),
  sameValue:(...args)=>sameValue(...args),
  shell:(...args)=>shell(...args),
  toast:(...args)=>toast(...args),
  uid:(...args)=>uid(...args),
});
const {reviewKey,reviewItemFromKey,selectedReviewItems,copyCitation,workspaceEvidenceKey,dbEvidenceKey,selectedEvidenceEntries,evidenceIsSelected,setEvidence,workspaceDbEvidenceTarget,workspaceEvidenceSelectionKey,toggleWorkspaceEvidence,toggleDbEvidence,clearSelectedEvidence,selectedEvidencePayload,setReviewSelected,clearReviewSelection}=createEvidenceSelection({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  fullCitation:(...args)=>fullCitation(...args),
  hasCapability:(...args)=>hasCapability(...args),
  inlineCitation:(...args)=>inlineCitation(...args),
  localRecordKey:(...args)=>localRecordKey(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  ragEvidenceRecordPayload:(...args)=>ragEvidenceRecordPayload(...args),
  recordDbStatus:(...args)=>recordDbStatus(...args),
  shellRefreshHook:(...args)=>shellRefreshHook(...args),
  storeReceipt:(...args)=>storeReceipt(...args),
  toast:(...args)=>toast(...args),
  tr:(...args)=>tr(...args),
  trf:(...args)=>trf(...args),
});
const {getUrlSyncHook,viewLabel,navSnapshot,sameSnapshot,applyNavSnapshot,setUrlSyncHook,currentTableUrlState,applyCompressedTableUrlState,urlFromState,syncUrl,applyUrlState,navigateTo,goBack,goForward}=createNavigation({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  activeFile:(...args)=>activeFile(...args),
  canAccessPage:(...args)=>canAccessPage(...args),
  dbSearchWhere:(...args)=>dbSearchWhere(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  renderView:(...args)=>renderView(...args),
  selectedIndex:(...args)=>selectedIndex(...args),
  shell:(...args)=>shell(...args),
});
const {openMessageModal,copyJsonToClipboard}=createModalDialogs({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  showAppModal:(...args)=>showAppModal(...args),
  toast:(...args)=>toast(...args),
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
  getUrlSyncHook:()=>getUrlSyncHook(),
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
const {recordDbStatus,workDbStatus,refreshPresenceForRows,updateDbStatusElements,ignoredFingerprint,pendingUpsertRows,pendingChangesForRow,removeFromUpsertQueue,buildUpsertItems,upsertRows,rowsFromReviewSelection}=createDbPresenceUpsert({
  state,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  allRows:(...args)=>allRows(...args),
  api:(...args)=>api(...args),
  candidateChromaIds:(...args)=>candidateChromaIds(...args),
  corpusCache:(...args)=>corpusCache(...args),
  corpusStoreExists:(...args)=>corpusStoreExists(...args),
  dbUnavailableReason:(...args)=>dbUnavailableReason(...args),
  formatTimestamp:(...args)=>formatTimestamp(...args),
  hasCorpusDb:(...args)=>hasCorpusDb(...args),
  localRecordKey:(...args)=>localRecordKey(...args),
  notifyVectorStoresChanged:(...args)=>notifyVectorStoresChanged(...args),
  openMessageModal:(...args)=>openMessageModal(...args),
  persistPrefs:(...args)=>persistPrefs(...args),
  recordFingerprint:(...args)=>recordFingerprint(...args),
  refreshOperationsPanelOnly:(...args)=>refreshOperationsPanelOnly(...args),
  reviewItemFromKey:(...args)=>reviewItemFromKey(...args),
  selectedReviewItems:(...args)=>selectedReviewItems(...args),
  startJobPolling:(...args)=>startJobPolling(...args),
  storeReceipt:(...args)=>storeReceipt(...args),
  syncJobProgressToasts:(...args)=>syncJobProgressToasts(...args),
  toast:(...args)=>toast(...args),
  tr:(...args)=>tr(...args),
  trf:(...args)=>trf(...args),
  upsertAuditDelta:(...args)=>upsertAuditDelta(...args),
  upsertRecordPayload:(...args)=>upsertRecordPayload(...args),
  workIndex:(...args)=>workIndex(...args),
});
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
const {persistFileNow,persistFile,workspacePrefs,persistPrefs,flushWorkspacePrefs,restoreWorkspace}=createWorkspacePersistence({
  state,
  fileTimers,
  // Wrapped so each helper is looked up when it is called: several are declared later in this module.
  applyUiTheme:(...args)=>applyUiTheme(...args),
  ensureProviderProfiles:(...args)=>ensureProviderProfiles(...args),
  idbGet:(...args)=>idbGet(...args),
  idbGetAll:(...args)=>idbGetAll(...args),
  idbPut:(...args)=>idbPut(...args),
  invalidateCorpusCache:(...args)=>invalidateCorpusCache(...args),
  restoreCurrentPdfAsset:(...args)=>restoreCurrentPdfAsset(...args),
  serializableFile:(...args)=>serializableFile(...args),
  toast:(...args)=>toast(...args),
});
// Subset files for the Vue Records view: the sources, fields and file creation, over the loaded files.
const {subsetSources,subsetSourceRecords,subsetFields,defaultSubsetName,createSubsetFile}=createRecordSubsets({
  state,
  cloneAuditValue,
  downloadBlob:(...args)=>downloadBlob(...args),
  label:(...args)=>label(...args),
  navigateTo:(...args)=>navigateTo(...args),
  persistFileNow:(...args)=>persistFileNow(...args),
  uid,
});
const {openMergeDialog,openBulkFieldEditor,openOcrCleanupDialog,openEditor,openStoreRecordEditor,openRecordHistoryBrowser,openUpsertQueue}=createRecordDialogs({
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
  fieldEditor:(...args)=>fieldEditor(...args),
  fileJsonl:(...args)=>fileJsonl(...args),
  fileTimers,
  formatTimestamp:(...args)=>formatTimestamp(...args),
  hasCorpusDb:(...args)=>hasCorpusDb(...args),
  historyVersionChanges:(...args)=>historyVersionChanges(...args),
  idbDelete:(...args)=>idbDelete(...args),
  jsonPretty:(...args)=>jsonPretty(...args),
  label:(...args)=>label(...args),
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
  selectedIndex:(...args)=>selectedIndex(...args),
  selectedRecord:(...args)=>selectedRecord(...args),
  selectedReviewItems:(...args)=>selectedReviewItems(...args),
  shell:(...args)=>shell(...args),
  showAppModal:(...args)=>showAppModal(...args),
  toast:(...args)=>toast(...args),
  tr:(...args)=>tr(...args),
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


function formatTimestamp(value){
  if(!value)return "";
  const date=new Date(value);
  return Number.isNaN(date.getTime())?String(value):date.toLocaleString();
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














// Names of the facts shown for an operation (panel rows and the details dialog), translated at render time.











// ---- Operations panel bridge -------------------------------------------------------------
// The panel itself is a Vue component (components/OperationsPanel.vue). The runtime still owns
// job state, the dock, toasts, and the details/results dialogs, so the panel reads a plain view
// model from here and calls back into the existing functions.










function compactNumber(value){const n=Number(value)||0;if(n>=1000000)return `${(n/1000000).toFixed(n>=10000000?0:1)}M`;if(n>=1000)return `${(n/1000).toFixed(n>=100000?0:1)}K`;return n.toLocaleString()}
function relativeTime(value){return relativeTimeLabel(value,Date.now(),{tr,trf,locale:state.translations?.locale})}





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
  else result=null;
  Promise.resolve(result).finally(()=>requestAnimationFrame(()=>{enhanceCollapsibles(main);decorateDisabledControls(main);translateLegacyDom(main)}));
  return result;
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
  subsetSources,
  subsetSourceRecords,
  subsetFields,
  defaultSubsetName,
  createSubsetFile,
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
  openMessageModal,
  formatTimestamp,
  refreshStores,
  responseCacheStore,
  enhanceCollapsibles,
  renderDashboard,
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
