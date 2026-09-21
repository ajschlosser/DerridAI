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
const {dashboardTotals,dashboardWorkspaceRecordTarget,dashboardRecordPreview,renderDashboard}=createDashboardRenderer({
  state,
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
function openRecordHistoryBrowser(file,index){
  const record=file?.records?.[index];
  if(!record)return;
  let versions=recordHistoryVersions(record);
  if(versions.length<=1)return toast("This record has no update history");
  let cursor=versions.length-1;
  const dialog=document.createElement("dialog");
  dialog.className="record-history-dialog";
  const close=()=>{dialog.close();dialog.remove()};
  const render=()=>{
    versions=recordHistoryVersions(file.records[index]);
    cursor=Math.max(0,Math.min(cursor,versions.length-1));
    const version=versions[cursor];
    const previous=cursor>0?versions[cursor-1]:null;
    const changed=previous?historyVersionChanges(previous.record,version.record):[];
    const currentIndex=versions.length-1;
    const isCurrent=cursor===currentIndex;
    const text=String(version.record.text||"");
    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Record history</h2><div class="dialog-subtitle">${esc(file.records[index]?.record_id||`Record ${index+1}`)} · ${versions.length-1} saved change set${versions.length-1===1?"":"s"}</div></div><button class="btn icon-only" data-close title="${esc(tr("ui.close","Close"))}" aria-label="${esc(tr("ui.close","Close"))}">${icon("close")}</button></div>
      <div class="db record-history-body">
        <div class="history-version-nav">
          <button class="btn" id="historyOlder" ${cursor<=0?`disabled data-disabled-reason="Already at the original record."`:""}>← Older</button>
          <div class="history-version-position"><b>${esc(version.label)}${isCurrent?" · Current":""}</b><span>${version.timestamp?esc(formatTimestamp(version.timestamp)):"Before tracked edits"}${version.source?` · ${esc(version.source)}`:""}${version.model?` · ${esc(version.model)}`:""}</span></div>
          <button class="btn" id="historyNewer" ${cursor>=currentIndex?`disabled data-disabled-reason="Already at the newest version."`:""}>Newer →</button>
        </div>
        <div class="history-version-summary"><span><b>${changed.length}</b> field${changed.length===1?"":"s"} changed in this version</span><span><b>${text.trim()?text.trim().split(/\s+/).length:0}</b> words</span><span><b>${text.length.toLocaleString()}</b> characters</span></div>
        ${changed.length?`<div class="history-version-diffs">${changed.map(field=>`<details class="history-version-diff"><summary><b>${esc(label(field))}</b><span>changed</span></summary><div class="history-diff-values"><div><small>Previous</small><pre>${esc(jsonPretty(previous?.record?.[field]))}</pre></div><div><small>This version</small><pre>${esc(jsonPretty(version.record?.[field]))}</pre></div></div></details>`).join("")}</div>`:`<div class="info">This is the reconstructed original state before tracked updates.</div>`}
        <details class="history-record-preview"><summary>Preview this version</summary><div class="history-preview-meta"><b>${esc(version.record.work||"Untitled work")}</b><span>${esc(version.record.document_author||"")} · ${esc(version.record.year||"")}</span></div><div class="history-preview-text">${esc(text.slice(0,5000))}${text.length>5000?"…":""}</div></details>
      </div>
      <div class="da record-history-actions"><button class="btn danger secondary-danger" id="historyClear">Delete audit history…</button><span class="dialog-action-spacer"></span><button class="btn" data-close>Close</button><button class="btn" id="historyUndoAll" ${cursor===0&&isCurrent?"disabled":""}>Restore original</button><button class="btn primary" id="historyRestore" ${isCurrent?`disabled data-disabled-reason="This is already the current version."`:""}>Restore this version</button></div>`;
    dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
    dialog.querySelector("#historyOlder").onclick=()=>{cursor--;render()};
    dialog.querySelector("#historyNewer").onclick=()=>{cursor++;render()};
    dialog.querySelector("#historyRestore").onclick=async()=>{
      if(isCurrent)return;
      const count=restoreRecordHistoryVersion(file,index,version);
      if(!count)return toast("No record fields needed restoring");
      versions=recordHistoryVersions(file.records[index]);cursor=versions.length-1;
      shell();renderView();render();
      toast(`Restored ${count} field${count===1?"":"s"} from ${version.label}`);
    };
    dialog.querySelector("#historyUndoAll").onclick=async()=>{
      const original=versions[0];
      if(!await openMessageModal({title:"Restore original record?",message:"Restore every field to its state before the tracked update history? The restoration itself will be recorded, so you can move forward again later.",confirmLabel:"Restore original",cancelLabel:"Cancel"}))return;
      const count=restoreRecordHistoryVersion(file,index,original);
      if(!count)return toast("The record already matches its original tracked state");
      versions=recordHistoryVersions(file.records[index]);cursor=versions.length-1;
      shell();renderView();render();
      toast(`Restored original record state · ${count} fields changed`);
    };
    dialog.querySelector("#historyClear").onclick=async()=>{
      if(!await clearRecordUpdates(file,index))return;
      close();shell();renderView();toast("Record update history cleared");
    };
    decorateDisabledControls(dialog);
  };
  document.body.appendChild(dialog);showAppModal(dialog);render();
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

function toast(message,{tone="auto",duration=null}={}){
  let el=document.querySelector("#toast");
  if(!el){el=document.createElement("div");el.id="toast";el.className="toast";document.body.appendChild(el)}
  // Toast text is operational information: keep it selectable/copyable and
  // pause dismissal while the user is interacting with it.
  el.setAttribute("role","status");
  el.setAttribute("aria-live","polite");
  el.setAttribute("aria-atomic","true");
  el.tabIndex=0;
  const text=translateDynamicUiValue(String(message??""));
  const failed=tone==="danger"||/\bHTTP\s+\d{3}\b/i.test(text)||/\b(failed|could not|error)\b/i.test(text);
  el.classList.toggle("failed",failed);
  el.classList.toggle("success",tone==="success");
  const httpIndex=text.search(/\bHTTP\s+\d{3}\b/i);
  if(failed&&httpIndex>=0){
    el.innerHTML=`${esc(text.slice(0,httpIndex))}<strong>${esc(text.slice(httpIndex))}</strong>`;
  }else{
    el.textContent=text;
  }
  el.classList.add("show");
  const dismissDelay=duration??(failed?8000:4200);
  const pause=()=>clearTimeout(el._timer);
  const resume=()=>{clearTimeout(el._timer);el._timer=setTimeout(()=>el.classList.remove("show"),dismissDelay)};
  el.onpointerenter=pause;
  el.onpointerleave=resume;
  el.onfocusin=pause;
  el.onfocusout=resume;
  resume();
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
async function openUpsertQueue(){
  if(!hasCorpusDb())return openMessageModal({title:"Vector database required",message:dbUnavailableReason(),confirmLabel:"OK"});
  if(!state.activeStore)return toast("Select a Chroma collection first");
  if(allRows().length)await refreshPresenceForRows(allRows());
  const rows=pendingUpsertRows();
  const dialog=document.createElement("dialog");
  dialog.className="queue-dialog wide-queue-dialog";

  const render=()=>{
    const currentRows=pendingUpsertRows();
    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(tr("vector.unsynced_changes","Unsynced local changes"))}</h2><div class="dialog-subtitle">${esc(state.activeStore)} · ${currentRows.length} ${esc(tr("dynamic.records","records"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db">
      <div class="queue-explainer"><b>${esc(tr("vector.unsynced_changes_what","What is this list?"))}</b><p>${esc(tr("vector.unsynced_changes_help","These are browser-workspace records that changed since their last confirmed sync, plus records DerridAI has confirmed are missing from the selected collection. Removing an item suppresses only its current version; a later change queues it again."))}</p></div><div class="queue-bulk-actions">${currentRows.length?`<button class="btn small" id="queueSelectAll">${esc(tr("ui.select_all","Select all"))}</button><button class="btn small" id="queueSelectNone">${esc(tr("ui.clear_selection","Clear selection"))}</button>`:""}</div>
      <div class="upsert-queue-list">${currentRows.map(row=>{
        const info=recordDbStatus(row.file,row.index,row.record);
        const key=localRecordKey(row.file,row.index);
        const changes=pendingChangesForRow(row);
        return `<section class="upsert-queue-card">
          <div class="upsert-queue-head">
            <label class="upsert-queue-item"><input type="checkbox" data-upsert-key="${esc(key)}" checked><span><b>${esc(row.record.record_id||`Record ${row.index+1}`)}</b><small>${esc(row.record.work||row.file.name)} · ${esc(row.file.name)}</small></span><span class="db-status ${info.kind}"><i></i>${esc(info.label)}</span></label>
            <div class="tools"><button class="btn small" data-review-queue="${esc(key)}">Review ${changes.length} change${changes.length===1?"":"s"}</button><button class="btn small danger" data-remove-queue="${esc(key)}">Remove from queue</button></div>
          </div>
          <div class="queue-change-list hidden" data-queue-changes="${esc(key)}">${changes.map(change=>`<div class="queue-change-row"><b>${esc(label(change.field_name||"field"))}</b><span>${esc(change.source||"manual")}${change.timestamp?` · ${esc(formatTimestamp(change.timestamp))}`:""}</span><details><summary>Values</summary><div class="queue-change-values"><pre>${esc(jsonPretty(change.old_value))}</pre><span>→</span><pre>${esc(jsonPretty(change.new_value))}</pre></div></details></div>`).join("")}</div>
        </section>`;
      }).join("")||`<div class="llm-empty">${esc(tr("vector.no_unsynced_changes","No confirmed unsynced local changes."))}</div>`}</div>
    </div>
    <div class="da"><button class="btn" data-close>Close</button>${currentRows.length?`<button class="btn primary" id="upsertQueued">${icon("database")}${esc(tr("vector.sync_selected","Sync selected"))}</button>`:""}</div>`;

    const close=()=>{dialog.close();dialog.remove()};
    dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
    dialog.querySelector("#queueSelectAll")?.addEventListener("click",()=>dialog.querySelectorAll("[data-upsert-key]").forEach(box=>box.checked=true));
    dialog.querySelector("#queueSelectNone")?.addEventListener("click",()=>dialog.querySelectorAll("[data-upsert-key]").forEach(box=>box.checked=false));
    dialog.querySelectorAll("[data-review-queue]").forEach(button=>button.onclick=()=>{
      const panel=dialog.querySelector(`[data-queue-changes="${CSS.escape(button.dataset.reviewQueue)}"]`);
      panel?.classList.toggle("hidden");
    });
    dialog.querySelectorAll("[data-remove-queue]").forEach(button=>button.onclick=()=>{
      const row=currentRows.find(item=>localRecordKey(item.file,item.index)===button.dataset.removeQueue);
      if(row){removeFromUpsertQueue(row);render();shell()}
    });
    dialog.querySelector("#upsertQueued")?.addEventListener("click",async()=>{
      const selected=new Set([...dialog.querySelectorAll("[data-upsert-key]:checked")].map(x=>x.dataset.upsertKey));
      const chosen=currentRows.filter(row=>selected.has(localRecordKey(row.file,row.index)));
      if(!chosen.length)return toast("Select at least one queued record");
      close();
      await upsertRows(chosen,"queued records");
      shell();renderView();
    });
  };

  document.body.appendChild(dialog);
  showAppModal(dialog);
  render();
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
function openMergeDialog(){
  if(state.files.length<2)return toast("Open at least two JSONL files to merge");
  const dialog=document.createElement("dialog");
  dialog.className="merge-dialog";
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Merge JSONL tabs</h2><div class="dialog-subtitle">Choose any subset. The selected source tabs will be replaced in the workspace by the merged tab.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db"><div class="merge-actions"><button class="btn small" id="mergeSelectAll">Select all</button><button class="btn small" id="mergeSelectNone">Clear</button></div><div class="merge-file-list">${state.files.map(file=>`<label class="merge-file-item"><input type="checkbox" data-merge-file="${file.id}" checked><span><b>${esc(file.name)}</b><small>${file.records.length.toLocaleString()} records</small></span></label>`).join("")}</div><div class="field"><label>Merged file name</label><input class="control" id="mergeName" value="derridai-merged.jsonl"></div><label class="check-item"><input type="checkbox" id="mergeDownload"><span>Download merged JSONL immediately</span></label><div class="info">Unselected tabs remain unchanged. Selected tabs are removed from the workspace after the merge is created; their underlying source files on disk are not deleted.</div></div><div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="mergeCreate">Merge and replace selected tabs</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(x=>x.onclick=close);
  dialog.querySelector("#mergeSelectAll").onclick=()=>dialog.querySelectorAll("[data-merge-file]").forEach(x=>x.checked=true);
  dialog.querySelector("#mergeSelectNone").onclick=()=>dialog.querySelectorAll("[data-merge-file]").forEach(x=>x.checked=false);
  dialog.querySelector("#mergeCreate").onclick=async()=>{
    const ids=[...dialog.querySelectorAll("[data-merge-file]:checked")].map(x=>x.dataset.mergeFile);
    const files=state.files.filter(file=>ids.includes(file.id));
    if(!files.length)return toast("Select at least one file");
    const firstIndex=Math.min(...files.map(file=>state.files.indexOf(file)));
    const name=(dialog.querySelector("#mergeName").value.trim()||"derridai-merged.jsonl").replace(/\s+/g,"-");
    const records=files.flatMap(file=>file.records.map(record=>cloneAuditValue(record)));
    const merged={
      id:uid(),
      name:name.endsWith(".jsonl")?name:`${name}.jsonl`,
      records,
      errors:files.flatMap(file=>file.errors||[]),
      dirty:new Set(records.map((_,index)=>index)),
      imported_at:new Date().toISOString(),
      merged_from:files.map(file=>file.name),
    };

    const removedIds=new Set(files.map(file=>file.id));
    state.files=state.files.filter(file=>!removedIds.has(file.id));
    state.files.splice(firstIndex,0,merged);

    for(const id of removedIds){
      delete state.selected[id];
      delete state.searches[id];
      delete state.pages[id];
      delete state.sorts[id];
      if(fileTimers.has(id)){
        clearTimeout(fileTimers.get(id));
        fileTimers.delete(id);
      }
      await idbDelete("files",id).catch(error=>console.error("Could not remove merged source tab from IndexedDB",error));
    }
    state.reviewSelection=new Set([...state.reviewSelection].filter(key=>!removedIds.has(String(key).split("::")[0])));
    for(const store of Object.keys(state.upsertState||{})){
      for(const key of Object.keys(state.upsertState[store]||{})){
        if(removedIds.has(String(key).split("::")[0]))delete state.upsertState[store][key];
      }
    }
    for(const store of Object.keys(state.upsertIgnored||{})){
      for(const key of Object.keys(state.upsertIgnored[store]||{})){
        if(removedIds.has(String(key).split("::")[0]))delete state.upsertIgnored[store][key];
      }
    }
    for(const bucket of [state.storePresence,state.storePresenceIds]){
      for(const store of Object.keys(bucket||{})){
        for(const key of Object.keys(bucket[store]||{})){
          if(removedIds.has(String(key).split("::")[0]))delete bucket[store][key];
        }
      }
    }

    await persistFileNow(merged);
    state.activeFileId=merged.id;
    if(dialog.querySelector("#mergeDownload").checked)download(merged.name,fileJsonl(merged));
    persistPrefs();
    close();
    navigateTo("list",{fileId:merged.id});
    toast(`Merged and replaced ${files.length} tabs · ${records.length.toLocaleString()} records`);
  };
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

let operationDockResizeWired=false;

function applyOperationStackPosition(stack){
  if(!stack)return;
  const position=state.operationStackPosition;
  if(!position){
    stack.style.left="";
    stack.style.top="";
    stack.style.right="";
    stack.style.bottom="";
    stack.style.transform="";
    stack.style.translate="";
    stack.style.removeProperty("--operation-stack-max-height");
    stack.classList.remove("user-positioned");
    return;
  }
  const rect=stack.getBoundingClientRect();
  const maxLeft=Math.max(8,window.innerWidth-Math.max(rect.width,280)-8);
  const maxTop=Math.max(8,window.innerHeight-52);
  const left=Math.min(maxLeft,Math.max(8,Number(position.left)||8));
  const top=Math.min(maxTop,Math.max(8,Number(position.top)||8));
  state.operationStackPosition={left,top};
  stack.style.left=`${left}px`;
  stack.style.top=`${top}px`;
  stack.style.right="auto";
  stack.style.bottom="auto";
  stack.style.translate="none";
  stack.style.setProperty("--operation-stack-max-height",`${Math.max(120,window.innerHeight-top-8)}px`);
  stack.classList.add("user-positioned");
}
function setOperationDockMinimized(minimized){
  state.operationToastsMinimized=Boolean(minimized);
  persistPrefs();
  const stack=document.querySelector("#operationProgressStack");
  if(!stack)return;
  stack.classList.toggle("minimized",state.operationToastsMinimized);
  stack.dataset.surface=state.operationToastsMinimized?"glass":"overlay";
  const toggle=stack.querySelector("#operationStackToggle");
  if(toggle){
    toggle.setAttribute("aria-expanded",state.operationToastsMinimized?"false":"true");
    toggle.setAttribute("aria-label",state.operationToastsMinimized
      ?tr("operations.expand","Show operations")
      :tr("operations.collapse","Hide operations"));
  }
  applyOperationStackPosition(stack);
  updateOperationStackCount();
}
function announceOperationDock(message){
  const live=document.querySelector("#operationStackLive");
  if(!live||!message)return;
  live.textContent="";
  live.textContent=message;
}
function operationDockCardStats(stack){
  let active=0,failed=0,finished=0,primaryLabel="",primaryPercent=null;
  stack.querySelectorAll(".operation-progress").forEach(panel=>{
    const job=panel.dataset.jobOperation?state.jobs.find(item=>item.id===panel.dataset.jobOperation):null;
    if(job){
      if(isActiveJobStatus(job.status)){
        active+=1;
        if(!primaryLabel){
          primaryLabel=jobLabel(job);
          primaryPercent=jobProgressPercent(job);
        }
      }else if(job.status==="failed")failed+=1;
      else finished+=1;
      return;
    }
    if(panel.classList.contains("failed")){failed+=1;return;}
    if(panel.classList.contains("operation-complete")){finished+=1;return;}
    active+=1;
    if(!primaryLabel){
      primaryLabel=panel.querySelector("b")?.textContent||"";
      const width=panel.querySelector("[data-progress-bar], .operation-progress-track i")?.style?.width||"";
      const parsed=Number.parseInt(width,10);
      primaryPercent=Number.isNaN(parsed)?null:parsed;
    }
  });
  return {active,failed,finished,primaryLabel,primaryPercent};
}
function wireOperationStackDrag(stack){
  const handle=stack?.querySelector("[data-operation-drag]");
  if(!handle||handle.dataset.dragWired)return;
  handle.dataset.dragWired="1";
  handle.addEventListener("pointerdown",event=>{
    if(event.button!==0||event.target.closest("button"))return;
    event.preventDefault();
    const rect=stack.getBoundingClientRect();
    const startX=event.clientX,startY=event.clientY,startLeft=rect.left,startTop=rect.top,width=rect.width;
    const maxLeft=Math.max(8,window.innerWidth-width-8);
    const maxTop=Math.max(8,window.innerHeight-52);
    let nextLeft=startLeft,nextTop=startTop,frame=0;
    handle.classList.add("dragging");
    stack.classList.add("is-dragging");
    stack.style.translate="none";
    stack.style.left=`${startLeft}px`;
    stack.style.top=`${startTop}px`;
    stack.style.right="auto";
    stack.style.bottom="auto";
    try{handle.setPointerCapture(event.pointerId)}catch{/* pointer capture is optional on this surface */}
    const paint=()=>{
      frame=0;
      stack.style.transform=`translate3d(${Math.round(nextLeft-startLeft)}px,${Math.round(nextTop-startTop)}px,0)`;
    };
    const move=e=>{
      nextLeft=Math.min(maxLeft,Math.max(8,startLeft+(e.clientX-startX)));
      nextTop=Math.min(maxTop,Math.max(8,startTop+(e.clientY-startY)));
      if(!frame)frame=requestAnimationFrame(paint);
    };
    const done=e=>{
      if(frame)cancelAnimationFrame(frame);
      stack.style.transform="";
      state.operationStackPosition={left:Math.round(nextLeft),top:Math.round(nextTop)};
      applyOperationStackPosition(stack);
      handle.classList.remove("dragging");
      stack.classList.remove("is-dragging");
      window.removeEventListener("pointermove",move);
      window.removeEventListener("pointerup",done);
      window.removeEventListener("pointercancel",done);
      try{handle.releasePointerCapture(e?.pointerId)}catch{/* pointer capture is optional on this surface */}
      persistPrefs();
    };
    window.addEventListener("pointermove",move,{passive:true});
    window.addEventListener("pointerup",done,{once:true});
    window.addEventListener("pointercancel",done,{once:true});
  });
  handle.addEventListener("dblclick",event=>{
    if(event.target.closest("button"))return;
    state.operationStackPosition=null;
    persistPrefs();
    applyOperationStackPosition(stack);
  });
  handle.addEventListener("keydown",event=>{
    if(event.key==="Escape"){
      if(!state.operationToastsMinimized){
        event.preventDefault();
        setOperationDockMinimized(true);
      }
      return;
    }
    if(!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(event.key)||event.target.closest("button"))return;
    event.preventDefault();
    const rect=stack.getBoundingClientRect();
    const step=event.shiftKey?40:12;
    let left=rect.left,top=rect.top;
    if(event.key==="ArrowLeft")left-=step;
    if(event.key==="ArrowRight")left+=step;
    if(event.key==="ArrowUp")top-=step;
    if(event.key==="ArrowDown")top+=step;
    state.operationStackPosition={left:Math.round(Math.max(8,Math.min(window.innerWidth-220,left))),top:Math.round(Math.max(8,Math.min(window.innerHeight-52,top)))};
    persistPrefs();
    applyOperationStackPosition(stack);
  });
  if(!operationDockResizeWired){
    operationDockResizeWired=true;
    window.addEventListener("resize",()=>applyOperationStackPosition(document.querySelector("#operationProgressStack")),{passive:true});
  }
}

function progressStack(){
  let stack=document.querySelector("#operationProgressStack");
  if(!stack){
    const dragHelp=tr("operations.drag_help","Drag anywhere · double-click to recenter");
    const title=tr("operations.title","Operations");
    stack=document.createElement("aside");
    stack.id="operationProgressStack";
    stack.className=`operation-progress-stack${state.operationToastsMinimized?" minimized":""}`;
    stack.dataset.surface=state.operationToastsMinimized?"glass":"overlay";
    stack.setAttribute("role","complementary");
    stack.setAttribute("aria-label",title);
    stack.innerHTML=`<div class="operation-stack-toolbar" data-operation-drag tabindex="0" role="group" aria-label="${esc(dragHelp)}" title="${esc(dragHelp)}"><span class="operation-drag-grip" aria-hidden="true"></span><button type="button" class="operation-dock-toggle" id="operationStackToggle" aria-expanded="${state.operationToastsMinimized?"false":"true"}" aria-controls="operationStackItems" aria-label="${esc(state.operationToastsMinimized?tr("operations.expand","Show operations"):tr("operations.collapse","Hide operations"))}"><span class="operation-dock-dot" aria-hidden="true"></span><span class="operation-dock-copy"><b class="operation-dock-title">${esc(title)}</b><span id="operationStackCount"></span></span><span class="operation-dock-chevron" aria-hidden="true"></span></button><button type="button" class="btn tiny operation-dock-clear" id="operationStackClearFinished" hidden>${esc(tr("operations.clear_finished","Clear finished"))}</button></div><div id="operationStackLive" class="sr-only" aria-live="polite"></div><div id="operationStackItems" class="operation-stack-items"></div>`;
    document.body.appendChild(stack);
    wireOperationStackDrag(stack);
    applyOperationStackPosition(stack);
    stack.querySelector("#operationStackToggle").addEventListener("click",()=>setOperationDockMinimized(!state.operationToastsMinimized));
    stack.querySelector("#operationStackClearFinished").addEventListener("click",()=>clearFinishedOperations());
    stack.addEventListener("keydown",event=>{
      if(event.key==="Escape"&&!state.operationToastsMinimized&&!event.target.closest("input,textarea,select")){
        event.preventDefault();
        setOperationDockMinimized(true);
      }
    });
  }
  return stack.querySelector(".operation-stack-items")||stack;
}
function updateOperationStackCount(){
  const stack=document.querySelector("#operationProgressStack");
  if(!stack)return;
  const count=stack.querySelectorAll(".operation-progress").length;
  if(!shouldMountOperationDock(count)){
    stack.remove();
    return;
  }
  const stats=operationDockCardStats(stack);
  const summary=dockCollapsedSummary(stats);
  const label=stack.querySelector("#operationStackCount");
  if(label){
    label.textContent=trf(summary.key,summary.fallback,summary.values);
    // When there is nothing more specific to say, the summary falls back to the dock's own title; do not say it twice.
    label.hidden=label.textContent===tr("operations.title","Operations");
  }
  stack.dataset.tone=summary.tone;
  if(summary.percent==null)stack.style.removeProperty("--operation-dock-progress");
  else stack.style.setProperty("--operation-dock-progress",`${summary.percent}%`);
  const clear=stack.querySelector("#operationStackClearFinished");
  if(clear){
    const canClear=stats.failed+stats.finished>0;
    clear.hidden=!canClear||state.operationToastsMinimized;
    clear.disabled=!canClear;
  }
  const toggle=stack.querySelector("#operationStackToggle");
  if(toggle){
    toggle.setAttribute("aria-expanded",state.operationToastsMinimized?"false":"true");
    toggle.setAttribute("aria-label",state.operationToastsMinimized
      ?tr("operations.expand","Show operations")
      :tr("operations.collapse","Hide operations"));
  }
}
function showOperationProgress(title,total){
  const id=uid();
  const stack=progressStack();
  const panel=document.createElement("div");
  panel.className="operation-progress show";
  panel.dataset.operationId=id;
  panel.innerHTML=`<div class="operation-progress-head"><div><b>${esc(title)}</b><span data-progress-text>0 of ${total.toLocaleString()}</span></div><div class="spinner small-spinner"></div></div><div class="operation-progress-track"><i data-progress-bar style="width:0%"></i></div><div class="operation-progress-detail" data-progress-detail></div>`;
  stack.appendChild(panel);
  updateOperationStackCount();
  state.operationProgress[id]={title,total,done:0};
  return id;
}
function updateOperationProgress(id,done,total,detail=""){
  const panel=document.querySelector(`[data-operation-id="${CSS.escape(id)}"]`);
  if(!panel)return;
  const pct=Math.round(total?done/total*100:100);
  const text=panel.querySelector("[data-progress-text]");
  const bar=panel.querySelector("[data-progress-bar]");
  const detailEl=panel.querySelector("[data-progress-detail]");
  if(text)text.textContent=`${done.toLocaleString()} of ${total.toLocaleString()} (${pct}%)`;
  if(bar)bar.style.width=`${pct}%`;
  if(detailEl)detailEl.textContent=detail;
  state.operationProgress[id]={...(state.operationProgress[id]||{}),done,total,detail};
}
function hideOperationProgress(id,delay=200){
  // Completed foreground operations remain visible until the user dismisses
  // them. ``delay`` is retained for call-site compatibility but is no longer
  // used to auto-remove operation history.
  const panel=document.querySelector(`[data-operation-id="${CSS.escape(id)}"]`);
  if(!panel)return;
  panel.classList.add("show","operation-complete");
  panel.querySelector(".spinner")?.remove();
  const head=panel.querySelector(".operation-progress-head");
  if(head&&!head.querySelector("[data-dismiss-operation]")){
    const button=document.createElement("button");
    button.className="btn tiny";button.dataset.dismissOperation=id;button.textContent=tr("ui.dismiss","Dismiss");
    button.onclick=()=>{panel.remove();delete state.operationProgress[id];updateOperationStackCount()};
    head.appendChild(button);
  }
  state.operationProgress[id]={...(state.operationProgress[id]||{}),finished:true};
}







// Names of the facts shown for an operation (panel rows and the details dialog), translated at render time.

function ensureJobProgressCard(job){
  const stack=progressStack();
  let panel=stack.querySelector(`[data-job-operation="${CSS.escape(job.id)}"]`);
  if(!panel){
    panel=document.createElement("article");
    panel.className="operation-progress show";
    panel.dataset.jobOperation=job.id;
    stack.appendChild(panel);
  }
  const pct=jobProgressPercent(job);
  const active=isActiveJobStatus(job.status);
  const tone=statusBadgeTone(job.status);
  panel.classList.toggle("failed",job.status==="failed");
  panel.classList.toggle("operation-complete",isTerminalJobStatus(job.status));
  panel.dataset.tone=tone;
  const cancellationDetail=job.type==="llm"||job.type==="llm_tool"
    ?"Cancellation requested · interrupting the active model stream."
    : job.type==="rag"
      ?"Cancellation requested · interrupting model streaming or waiting for the current vector/rerank checkpoint."
      : job.type==="upsert"
        ?"Cancellation requested · the current Chroma batch will finish, then the job stops."
        : "Cancellation requested.";
  const detail=job.status==="cancelling"||job.cancel_requested
    ?cancellationDetail
    : job.status==="failed"
      ? trf("operations.failed_help","Failed · {detail}",{detail:String(job.fatal_error||job.stage_detail||"Operation failed")})
    : job.status==="completed"
      ? tr("operations.completed_help","Completed · open the result or dismiss")
    : job.status==="cancelled"
      ? tr("operations.cancelled_help","Cancelled · partial results may still be available")
    : job.type==="rag"
      ? `${job.stage_detail||job.stage||"Running RAG pipeline"}`
      : job.type==="upsert"
        ? `${job.store_name||"collection"} · ${job.completed}/${job.total} records committed`
        : job.type==="llm_tool"
          ? `${job.stage_detail||jobLabel(job)}`
          : `${job.failed?`${job.failed} failed · `:""}${job.current_record_id?`Reviewing ${job.current_record_id}`:"Background operation"}`;
  const httpIndex=String(detail).search(/\bHTTP\s+\d{3}\b/i);
  const detailHtml=httpIndex>=0
    ? `${esc(String(detail).slice(0,httpIndex))}<strong>${esc(String(detail).slice(httpIndex))}</strong>`
    : esc(detail);
  const canOpenResult=(job.type==="llm"&&Number(job.pending_result_count||0)>0)||(["rag","llm_tool"].includes(job.type)&&job.status==="completed")||(job.type==="pdf_corpus"&&["completed","blocked"].includes(job.status));
  const resultActionLabel=job.type==="pdf_corpus"
    ?tr("pdf_corpus.open_build","Open corpus build")
    :job.type==="llm_tool"&&(job.tool==="rag_grade"||job.mode==="rag_grade")
      ?tr("operations.view_grade","View grade")
      :tr("operations.open_result","Open result");
  const statusLabel=tr(`operations.status.${job.status}`,job.status);
  const provider=jobProviderSummary(job);
  const pending=Number(job.pending_result_count||0);
  const actions=[];
  if(active){
    if(job.cancel_requested||job.status==="cancelling")actions.push(`<span class="cancel-pending">${esc(tr("operations.cancelling","Cancelling…"))}</span>`);
    else actions.push(`<button type="button" class="btn tiny danger" data-toast-cancel-job="${job.id}">${esc(tr("ui.cancel","Cancel"))}</button>`);
  }else{
    if(canOpenResult)actions.push(`<button type="button" class="btn tiny primary" data-toast-open-result="${job.id}">${esc(resultActionLabel)}</button>`);
    if(job.type==="llm"&&pending>0)actions.push(`<button type="button" class="btn tiny primary" data-toast-review-results="${job.id}">${esc(trf("operations.review_available","Review {count} available",{count:pending}))}</button>`);
    actions.push(`<button type="button" class="btn tiny" data-toast-dismiss-job="${job.id}">${esc(tr("ui.dismiss","Dismiss"))}</button>`);
  }
  actions.push(`<button type="button" class="btn tiny" data-toast-open-details="${job.id}">${esc(tr("operations.open_details","Full details"))}</button>`);
  panel.innerHTML=`<div class="operation-progress-head"><div><b>${esc(jobLabel(job))}</b>${provider?`<small class="operation-progress-provider">${esc(provider)}</small>`:""}</div><span class="operation-status-badge" data-tone="${esc(tone)}"><span class="operation-status-dot" aria-hidden="true"></span>${esc(statusLabel)}</span></div><div class="operation-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="${esc(jobProgressText(job,"of"))}"><i style="width:${pct}%"></i></div><div class="operation-progress-detail">${detailHtml}</div><div class="operation-toast-actions">${actions.join("")}${active?'<div class="spinner small-spinner"></div>':""}</div>`;
  panel.querySelector("[data-toast-cancel-job]")?.addEventListener("click",()=>cancelBackgroundJob(job.id));
  panel.querySelector("[data-toast-review-results]")?.addEventListener("click",()=>openJobResults(job.id));
  panel.querySelectorAll("[data-toast-open-result]").forEach(button=>button.addEventListener("click",()=>openJobResults(job.id)));
  panel.querySelector("[data-toast-open-details]")?.addEventListener("click",()=>openJobDetails(job.id));
  panel.querySelector("[data-toast-dismiss-job]")?.addEventListener("click",()=>removeFinishedJob(job.id));
  updateOperationStackCount();
}

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

async function openJobDetails(jobId){
  let job;
  try{
    job=await api(`/api/jobs/${encodeURIComponent(jobId)}`);
  }catch(error){
    if(String(error?.message||"").includes("404")){
      pruneClientJobState(jobId);
      persistPrefs();
      if(state.view==="rag")refreshRagProgressPanel();
      return toast("This operation was removed and has been cleared from the activity view");
    }
    return toast(`Could not load operation details: ${error.message}`);
  }
  const dialog=document.createElement("dialog");
  dialog.className="job-details-dialog";
  const events=job.events||[];
  const request=job.request||{};
  const safeRequest=cloneAuditValue(request);
  if(safeRequest&&typeof safeRequest==="object")delete safeRequest.api_key;

  const resultSummary=job.type==="llm"
    ? {
        pending_result_count:job.pending_result_count??(job.results||[]).length,
        pending_proposed_changes:job.pending_change_count??(job.results||[]).reduce((sum,result)=>sum+Object.keys(result.proposal?.changes||{}).length,0),
        accepted_results:job.accepted_results||0,
        accepted_fields:job.accepted_fields||0,
        rejected_results:job.rejected_results||0,
        rejected_fields:job.rejected_fields||0,
        resolution_state:job.resolution_state||"pending",
        unprocessed_records:job.remaining_record_count??Math.max(0,(job.total||0)-(job.completed||0)),
        failures:(job.results||[]).filter(result=>result.error).length,
      }
    : job.type==="upsert"
      ? {
          committed:job.completed||0,
          requested:job.total||0,
          target_collection:job.store_name,
          language_mirrors:job.mirrored||{},
          receipt_count:(job.results||[]).length,
        }
      : job.type==="pdf_corpus"
        ? {
            source_pdf:job.source_filename||null,
            build_id:job.build_id||job.id,
            raw_status:job.raw_status||job.status,
            stage:job.stage||null,
            record_count:job.record_count||0,
            review_count:job.review_count||0,
            unresolved_regions:job.unresolved_regions||0,
          }
      : job.type==="llm_tool"
        ? {
            operation:job.label||job.tool||job.mode,
            provider_profile_id:job.provider_profile_id||null,
            max_concurrent_requests:job.max_concurrent_requests||null,
            has_result:Boolean(job.result),
            result_keys:job.result&&typeof job.result==="object"?Object.keys(job.result):[],
          }
        : {
            has_result:Boolean(job.result),
            evidence_count:job.result?.evidence?.length||0,
            elapsed_seconds:job.result?.elapsed_seconds??null,
            collections:job.result?.collections||[],
            response_cache:job.result?.response_cache||job.response_cache||null,
          };

  dialog.innerHTML=`<div class="dh">
    <div><h2 class="dialog-title">${esc(jobLabel(job))} details</h2><div class="dialog-subtitle">${esc(job.id)} · ${esc(job.status)} · created ${esc(formatTimestamp(job.created_at))}</div></div>
    <button class="btn icon-only" data-close>${icon("close")}</button>
  </div>
  <div class="db job-details-body">
    <section class="job-detail-summary">
      ${[
        ["Type",job.type],
        ["Started by",job.owner||"—"],
        ["Status",job.status],
        ["Provider",job.provider],
        ["Model",job.model],
        ["Progress",`${job.completed}/${job.total}`],
        ["Failed",job.failed||0],
        ["Started",job.started_at?formatTimestamp(job.started_at):"—"],
        ["Finished",job.finished_at?formatTimestamp(job.finished_at):"—"],
        ["Cancel requested",job.cancel_requested_at?formatTimestamp(job.cancel_requested_at):"—"],
      ].map(([name,value])=>`<div><span>${esc(name)}</span><b>${esc(value??"—")}</b></div>`).join("")}
    </section>
    ${job.fatal_error?`<div class="info error">${esc(job.fatal_error)}</div>`:""}
    <section class="card-inset">
      <div class="rag-result-section-head"><div><b>Request configuration</b><div class="note">API keys are intentionally omitted.</div></div></div>
      <pre class="job-detail-json">${esc(JSON.stringify(safeRequest,null,2))}</pre>
    </section>
    <section class="card-inset">
      <div class="rag-result-section-head"><div><b>Operation timeline</b><div class="note">${events.length} recorded events</div></div></div>
      <div class="job-event-list">${events.map((event,index)=>`<div class="job-event ${index===events.length-1?"latest":""}"><time>${esc(formatTimestamp(event.timestamp))}</time><b>${esc(label(event.stage||"event"))}</b><span>${event.current!=null&&event.total!=null?`${event.current}/${event.total} · `:""}${esc(event.detail||"")}</span></div>`).join("")||'<div class="note">No events recorded.</div>'}</div>
    </section>
    <section class="card-inset">
      <div class="rag-result-section-head"><b>Result summary</b></div>
      <pre class="job-detail-json">${esc(JSON.stringify(resultSummary,null,2))}</pre>
    </section>
  </div>
  <div class="da">
    <button class="btn" data-close>Close</button>
    ${["queued","running","cancelling"].includes(job.status)?(job.cancel_requested||job.status==="cancelling"?'<button class="btn" disabled>Cancelling…</button>':`<button class="btn danger" id="detailsCancelJob">Cancel operation</button>`):""}
    ${job.type==="llm"&&(job.pending_result_count??(job.results||[]).length)>0?`<button class="btn primary" id="detailsOpenResult">${["queued","running","cancelling"].includes(job.status)?"Review available results":"Review results"}</button>`:""}
    ${((["rag","llm_tool"].includes(job.type)&&job.status==="completed")||(job.type==="pdf_corpus"&&["completed","blocked"].includes(job.status)))?`<button class="btn primary" id="detailsOpenResult">${job.type==="pdf_corpus"?esc(tr("pdf_corpus.open_build","Open corpus build")):"Open result"}</button>`:""}
  </div>`;
  document.body.appendChild(dialog);
  showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#detailsCancelJob")?.addEventListener("click",async()=>{
    const updated=await cancelBackgroundJob(job.id);
    if(updated){close();openJobDetails(job.id)}
  });
  dialog.querySelector("#detailsOpenResult")?.addEventListener("click",()=>{close();openJobResults(job.id)});
}

function openReviewRecordPreview(local,result){
  const record=local?.file?.records?.[local.index];
  if(!record)return toast("The source record is no longer loaded in this workspace");

  const proposal=result?.proposal||{};
  const proposedFields=Object.keys(proposal.changes||{});
  const important=[
    "work","document_author","edition","year","page_start","page_end",
    "region_type","region_author","speaker","position_holder","target",
    "discourse_role","proposition_status","semantic_function","stance",
    "claim_scope","is_direct_quote","quoted_speaker","quoted_author",
    "quoted_work","quoted_position_holder","quoted_addressee",
    "quoted_referent","quotation_chain","topics","concepts","persons",
    "works_referenced","document_language","original_language",
    "inline_citation","full_citation","needs_review","review_reason"
  ].filter(field=>record[field]!==undefined);

  const dialog=document.createElement("dialog");
  dialog.className="record-preview-dialog";
  const stale=Boolean(result?.fingerprint&&recordFingerprint(record)!==result.fingerprint);
  const updates=Array.isArray(record.updates)?record.updates.slice(-8).reverse():[];

  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Record preview</h2><div class="dialog-subtitle">${esc(record.record_id||`Record ${local.index+1}`)} · ${esc(record.work||local.file.name)} · ${esc(local.file.name)}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db record-preview-body">
    ${stale?'<div class="info warn">This local record changed after the LLM job started. Current values below may differ from the values originally reviewed.</div>':""}
    <section class="record-preview-summary">
      <div><span>Record ID</span><b>${esc(record.record_id||"—")}</b></div>
      <div><span>Work</span><b>${esc(record.work||"—")}</b></div>
      <div><span>Pages</span><b>${esc(pages(record))}</b></div>
      <div><span>Citation</span><b>${esc(fullCitation(record)||"—")}</b></div>
      <div><span>LLM proposals</span><b>${proposedFields.length}</b></div>
      <div><span>Needs review</span><b>${record.needs_review?"Yes":"No"}</b></div>
    </section>

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>Metadata</b><span>${important.length} populated fields</span></div>
      <div class="record-preview-metadata">${important.map(field=>`<div class="record-preview-field ${proposedFields.includes(field)?"proposed-field":""}"><span>${esc(label(field))}${proposedFields.includes(field)?'<i>proposed change</i>':""}</span><pre>${esc(jsonPretty(record[field]))}</pre></div>`).join("")}</div>
    </section>

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>Text</b><span>${String(record.text||"").length.toLocaleString()} characters</span></div>
      <pre class="record-preview-text">${esc(record.text||"")}</pre>
    </section>

    ${proposedFields.length?`<section class="record-preview-section"><div class="record-preview-heading"><b>Proposed changes for this record</b><span>${proposedFields.length}</span></div><div class="record-preview-proposals">${proposedFields.map(field=>`<div><b>${esc(label(field))}</b><div class="record-preview-proposal-grid"><pre>${esc(jsonPretty(record[field]))}</pre><span>→</span><pre>${esc(jsonPretty(proposal.changes[field]))}</pre></div>${proposal.rationale?.[field]?`<small>${esc(proposal.rationale[field])}</small>`:""}</div>`).join("")}</div></section>`:""}

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>Recent audit history</b><span>${updates.length} shown</span></div>
      <div class="record-preview-history">${updates.map(update=>`<div><time>${esc(formatTimestamp(update.timestamp))}</time><b>${esc(label(update.field_name||"field"))}</b><span>${esc(update.source||"manual")}${update.initiated_by?` · ${esc(update.initiated_by)}`:""}</span></div>`).join("")||'<div class="note">No audit history recorded.</div>'}</div>
    </section>
  </div>
  <div class="da"><button class="btn" data-close>Close preview</button><button class="btn" data-copy-row-key="${esc(reviewKey(local.file,local.index))}">${icon("copy")}Copy entire record</button><button class="btn primary" id="previewOpenRecord">${icon("arrow")}Open full Record view</button></div>`;

  document.body.appendChild(dialog);
  showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#previewOpenRecord").onclick=()=>{
    close();
    navigateTo("record",{fileId:local.file.id,index:local.index});
  };
}


async function openJobResults(jobId){
  let job;
  try{job=await api(`/api/jobs/${encodeURIComponent(jobId)}`)}catch(error){
    if(String(error?.message||"").includes("404")){pruneClientJobState(jobId);persistPrefs();if(state.view==="rag")refreshRagProgressPanel();return toast("This operation was removed and has been cleared from the activity view")}
    await openMessageModal({title:"Could not open operation result",message:error.message||String(error),tone:"danger"});
    return;
  }
  try{
    if(job.type==="rag")return openRagResult(job);
    if(job.type==="llm_tool")return openLlmToolResult(job);
    if(job.type==="upsert")return openJobDetails(job.id);
    if(job.type==="pdf_corpus"){
      window.dispatchEvent(new CustomEvent("derridai:navigate-native",{detail:{path:`/pdf?mode=builder&build=${encodeURIComponent(job.build_id||job.id)}`,runtimeView:"pdf"}}));
      return;
    }
  }catch(error){
    console.error("Could not render operation result",error,job);
    await openMessageModal({title:"Could not render operation result",message:error.message||String(error),detail:jobLabel(job),tone:"danger"});
    return;
  }

  const dialog=document.createElement("dialog");
  dialog.className="job-results-dialog";
  document.body.appendChild(dialog);
  showAppModal(dialog);
  let liveTimer=null;

  async function refreshJob(){
    try{
      job=await api(`/api/jobs/${encodeURIComponent(jobId)}`);
      const idx=state.jobs.findIndex(item=>item.id===job.id);
      if(idx>=0)state.jobs[idx]={...state.jobs[idx],...job};
      return true;
    }catch(error){
      toast(`Could not refresh review results: ${error.message}`);
      return false;
    }
  }

  function buildData(){
    const successful=(job.results||[]).filter(result=>!result.error&&result.proposal);
    const failures=(job.results||[]).filter(result=>result.error);
    const unchanged=[];
    const flattened=[];
    for(const result of successful){
      const local=reviewItemFromKey(result.key);
      const currentRecord=local?.file.records[local.index];
      const stale=Boolean(local&&result.fingerprint&&recordFingerprint(currentRecord)!==result.fingerprint);
      const changes=Object.entries(result.proposal?.changes||{});
      if(!changes.length){
        unchanged.push({result,local,stale});
        continue;
      }
      for(const [field,proposed] of changes){
        flattened.push({
          result,local,field,
          current:currentRecord?.[field],
          proposed,
          rationale:result.proposal?.rationale?.[field]||"",
          stale,
        });
      }
    }
    return {successful,failures,unchanged,flattened};
  }

  let selections=new Set();

  function initializeSelections(flattened){
    const valid=[...selections].filter(index=>index<flattened.length);
    selections=new Set(valid);
    if(!selections.size){
      flattened.forEach((item,index)=>{if(item.field!=="text")selections.add(index)});
    }
  }

  async function resolveOnServer(action,items,{dismissJob=false}={}){
    return api(`/api/jobs/${encodeURIComponent(job.id)}/llm-results/resolve`,{
      method:"POST",
      body:JSON.stringify({action,items,dismiss_job:dismissJob}),
    });
  }

  async function rejectAndDismiss(){
    if(!await openMessageModal({title:"Discard pending LLM review?",message:"Discard all currently pending proposed changes, stop the review if it is still running, and remove this operation from the queue?",tone:"danger",confirmLabel:"Discard pending & remove",cancelLabel:"Keep review"}))return;
    try{
      await api(`/api/jobs/${encodeURIComponent(job.id)}/llm-results/reject`,{
        method:"POST",
        body:JSON.stringify({dismiss:true}),
      });
      dialog.close();dialog.remove();
      await refreshJobs({rerender:state.view==="home"});
      toast("LLM review rejected and removed from the operations queue");
    }catch(error){
      toast(`Could not reject LLM review: ${error.message}`);
    }
  }

  async function apply(mode){
    const {successful,unchanged,flattened}=buildData();
    const batchId=uid();
    let fieldsApplied=0;
    let fullyReviewed=0;
    const resolveItems=[];
    const byKey=new Map();

    for(const result of successful){
      const local=reviewItemFromKey(result.key);
      if(local){
        byKey.set(result.key,{
          item:local,
          result,
          fields:[],
          allFields:Object.keys(result.proposal?.changes||{}),
          rationale:result.proposal?.rationale||{},
          resolveRecord:false,
        });
      }
    }

    if(mode==="review"){
      for(const entry of byKey.values())entry.resolveRecord=true;
    }else if(mode==="all"){
      for(const entry of byKey.values()){
        entry.fields=[...entry.allFields];
        entry.resolveRecord=true;
      }
    }else{
      flattened.forEach((entry,index)=>{
        if(!selections.has(index)||!entry.local)return;
        const target=byKey.get(entry.result.key);
        if(target)target.fields.push(entry.field);
      });
      for(const target of byKey.values()){
        if(target.fields.length&&target.fields.length===target.allFields.length){
          target.resolveRecord=true;
        }
      }
    }

    for(const [key,target] of byKey.entries()){
      if(mode==="selected"&&!target.fields.length)continue;
      const record=target.item.file.records[target.item.index];
      const changes={};
      if(mode!=="review"){
        const sourceChanges=target.result.proposal?.changes||{};
        for(const field of target.fields){
          if(field in sourceChanges)changes[field]=sourceChanges[field];
        }
      }

      // Clear needs_review only when the full pending proposal for this record
      // is being resolved, or the user explicitly chose "mark reviewed only".
      if(target.resolveRecord){
        if(record.needs_review!==false)changes.needs_review=false;
        if(record.review_reason!=null&&record.review_reason!=="")changes.review_reason=null;
      }
      fieldsApplied+=applyRecordChanges(
        target.item.file,
        target.item.index,
        changes,
        {
          source:"llm_review",
          model:job.model,
          batchId,
          rationale:target.rationale,
        }
      );
      if(target.resolveRecord)fullyReviewed++;

      resolveItems.push({
        key,
        fields:target.resolveRecord?null:target.fields,
        resolve_record:target.resolveRecord,
      });
    }

    if(mode==="review"){
      for(const entry of unchanged){
        if(!entry.local)continue;
        const record=entry.local.file.records[entry.local.index];
        const changes={};
        if(record.needs_review!==false)changes.needs_review=false;
        if(record.review_reason!=null&&record.review_reason!=="")changes.review_reason=null;
        fieldsApplied+=applyRecordChanges(
          entry.local.file,
          entry.local.index,
          changes,
          {source:"llm_review",model:job.model,batchId,rationale:{}}
        );
        fullyReviewed++;
        resolveItems.push({key:entry.result.key,fields:null,resolve_record:true});
      }
    }else if(mode==="all"){
      for(const entry of unchanged){
        if(!entry.local)continue;
        const record=entry.local.file.records[entry.local.index];
        const changes={};
        if(record.needs_review!==false)changes.needs_review=false;
        if(record.review_reason!=null&&record.review_reason!=="")changes.review_reason=null;
        fieldsApplied+=applyRecordChanges(
          entry.local.file,
          entry.local.index,
          changes,
          {source:"llm_review",model:job.model,batchId,rationale:{}}
        );
        fullyReviewed++;
        resolveItems.push({key:entry.result.key,fields:null,resolve_record:true});
      }
    }

    if(!resolveItems.length)return toast("No LLM results selected");

    try{
      job=await resolveOnServer("accept",resolveItems);
      state.jobApplied[job.id]=new Date().toISOString();
      persistPrefs();
      shell();renderView();
      await refreshJobs({rerender:state.view==="home"});
      selections.clear();
      render({preserveScroll:true});
      toast(`Accepted ${resolveItems.length} pending result${resolveItems.length===1?"":"s"} · ${fieldsApplied} tracked field changes · ${job.pending_result_count||0} pending`);
    }catch(error){
      toast(`Local changes were applied, but the operation queue could not be updated: ${error.message}`);
    }
  }

  async function rejectSelected(){
    const {flattened}=buildData();
    const grouped=new Map();
    flattened.forEach((entry,index)=>{
      if(!selections.has(index))return;
      if(!grouped.has(entry.result.key))grouped.set(entry.result.key,[]);
      grouped.get(entry.result.key).push(entry.field);
    });
    const items=[...grouped.entries()].map(([key,fields])=>({key,fields,resolve_record:false}));
    if(!items.length)return toast("Select proposed changes to reject");
    try{
      job=await resolveOnServer("reject",items);
      selections.clear();
      await refreshJobs({rerender:state.view==="home"});
      render({preserveScroll:true});
      toast(`Rejected selected proposed changes · ${job.pending_change_count||0} pending changes remain`);
    }catch(error){
      toast(`Could not reject selected changes: ${error.message}`);
    }
  }

  function render({preserveScroll=false}={}){
    const tableBefore=dialog.querySelector(".job-change-table-wrap");
    const scrollState=preserveScroll?{dialog:dialog.scrollTop,tableTop:tableBefore?.scrollTop||0,tableLeft:tableBefore?.scrollLeft||0}:null;
    const {successful,failures,unchanged,flattened}=buildData();
    initializeSelections(flattened);
    const selected=selections.size;
    const changedRecords=new Set(flattened.map(item=>item.result.key)).size;
    const noChangeCount=unchanged.length;
    const active=["queued","running","cancelling"].includes(job.status);
    const statusText=job.status==="cancelled"?"cancelled with partial results":job.status;
    const pendingResults=job.pending_result_count??successful.length;
    const pendingChanges=job.pending_change_count??flattened.length;
    const remaining=job.remaining_record_count??Math.max(0,(job.total||0)-(job.completed||0));

    const changeTable=flattened.length?`<div class="job-change-table-wrap"><table class="job-change-table"><thead><tr><th></th><th>Record</th><th>Field</th><th>Current</th><th>Proposed</th><th>Rationale</th></tr></thead><tbody>${flattened.map((item,index)=>{
      const rid=item.local?.record?.record_id||item.result.record_id||item.result.key;
      const diff=reviewDiffSides(item.current,item.proposed);
      return `<tr class="${item.stale?"stale-change":""}"><td><input type="checkbox" data-job-change="${index}" ${selections.has(index)?"checked":""}></td><td><div class="job-record-cell"><b>${esc(rid)}</b>${item.local?`<button class="btn tiny" data-copy-row-key="${esc(reviewKey(item.local.file,item.local.index))}">${icon("copy")}Copy</button>`:""}<button class="btn tiny" data-preview-result="${index}">Preview record</button>${item.stale?'<span class="stale-badge">local record changed since job started</span>':""}</div></td><td><b>${esc(label(item.field))}</b></td><td><pre class="change-diff current-diff">${diff.left}</pre></td><td><pre class="change-diff proposed-diff">${diff.right}</pre></td><td>${esc(item.rationale||"No rationale supplied.")}</td></tr>`;
    }).join("")}</tbody></table></div>`:`<section class="review-no-changes-empty"><div class="review-no-changes-icon">✓</div><div><h3>${active?"No pending changes yet":"No changes proposed"}</h3><p>${active?`The review is still running. ${job.completed.toLocaleString()} records have completed and ${remaining.toLocaleString()} remain unprocessed.`:`The model reviewed ${noChangeCount.toLocaleString()} record${noChangeCount===1?"":"s"} and did not propose metadata/text edits.`}</p></div></section>`;

    const unchangedSection=noChangeCount?`<details class="unchanged-review-list" ${flattened.length?"":"open"}><summary><span><b>${noChangeCount.toLocaleString()} record${noChangeCount===1?"":"s"} with no proposed changes</b><small>Expand to inspect or preview these records</small></span></summary><div class="unchanged-review-grid">${unchanged.map((item,index)=>{const rid=item.local?.record?.record_id||item.result.record_id||item.result.key;return `<div class="unchanged-review-row"><div><b>${esc(rid)}</b><span>${esc(item.local?.record?.work||"")}${item.stale?" · local record changed since review":""}</span></div><button class="btn tiny" data-preview-unchanged="${index}">Preview record</button></div>`}).join("")}</div></details>`:"";

    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${job.mode==="auto"?"Auto-improve changes":"LLM review changes"}</h2><div class="dialog-subtitle">${job.completed}/${job.total} processed · ${pendingResults} pending result${pendingResults===1?"":"s"} · ${pendingChanges} pending change${pendingChanges===1?"":"s"} · ${remaining} unprocessed · ${failures.length} failures · ${esc(statusText)}</div></div><div class="tools">${active?'<span class="job-status running">live</span>':""}<button class="btn icon-only" data-close>${icon("close")}</button></div></div>
    <div class="db job-change-review">
      <div class="job-resolution-summary">
        <span><b>${job.accepted_results||0}</b> accepted results</span>
        <span><b>${job.accepted_fields||0}</b> accepted fields</span>
        <span><b>${job.rejected_results||0}</b> rejected results</span>
        <span><b>${job.rejected_fields||0}</b> rejected fields</span>
        <span><b>${esc((job.resolution_state||"pending").replaceAll("_"," "))}</b> decision state</span>
      </div>
      ${flattened.length?`<div class="job-change-toolbar"><button class="btn small" id="jobSelectAll">Select all changes</button><button class="btn small" id="jobSelectNone">Select none</button><button class="btn small danger" id="jobRejectSelected">Reject selected</button><span class="note"><b id="jobSelectedCount">${selected}</b> selected · accepted changes are removed from this pending queue immediately</span></div>`:""}
      ${failures.length?`<div class="info warn">${failures.map(result=>`${esc(result.record_id||result.key)}: ${esc(result.error?.message||"failed")}`).join("<br>")}</div>`:""}
      ${changeTable}
      ${unchangedSection}
    </div>
    <div class="da">
      <button class="btn" data-close>Close</button>
      ${active&&remaining>0?`<button class="btn danger subtle-danger" id="rejectJob">${icon("close")}Stop review & discard pending</button>`:pendingResults>0?`<button class="btn danger subtle-danger" id="rejectJob">${icon("close")}Discard pending & remove operation</button>`:""}
      ${active?`<button class="btn" id="refreshLiveResults">${icon("refresh")}Refresh available results</button>`:""}
      ${successful.length?`<button class="btn" id="markJobReviewed">${icon("check")}Mark all available reviewed</button>${flattened.length?`<button class="btn primary" id="applyJobSelected" ${selected?"":"disabled"}>${icon("check")}Apply selected</button><button class="btn soft" id="applyJobAll">${icon("check")}Accept all available</button>`:""}`:""}
    </div>`;

    const close=()=>{if(liveTimer)clearInterval(liveTimer);dialog.close();dialog.remove()};
    dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
    const syncSelectionUi=()=>{
      dialog.querySelectorAll("[data-job-change]").forEach(box=>{box.checked=selections.has(+box.dataset.jobChange)});
      const count=dialog.querySelector("#jobSelectedCount");if(count)count.textContent=String(selections.size);
      const applyButton=dialog.querySelector("#applyJobSelected");if(applyButton)applyButton.disabled=!selections.size;
    };
    dialog.querySelector("#jobSelectAll")?.addEventListener("click",()=>{flattened.forEach((_,index)=>selections.add(index));syncSelectionUi()});
    dialog.querySelector("#jobSelectNone")?.addEventListener("click",()=>{selections.clear();syncSelectionUi()});
    dialog.querySelector("#jobRejectSelected")?.addEventListener("click",rejectSelected);
    dialog.querySelector("#rejectJob")?.addEventListener("click",rejectAndDismiss);
    dialog.querySelector("#refreshLiveResults")?.addEventListener("click",async()=>{if(await refreshJob())render({preserveScroll:true})});
    dialog.querySelectorAll("[data-job-change]").forEach(box=>box.onchange=()=>{const index=+box.dataset.jobChange;box.checked?selections.add(index):selections.delete(index);syncSelectionUi()});
    dialog.querySelectorAll("[data-preview-result]").forEach(button=>button.onclick=()=>{const entry=flattened[+button.dataset.previewResult];if(entry?.local)openReviewRecordPreview(entry.local,entry.result);else toast("The source record is no longer loaded")});
    dialog.querySelectorAll("[data-preview-unchanged]").forEach(button=>button.onclick=()=>{const entry=unchanged[+button.dataset.previewUnchanged];if(entry?.local)openReviewRecordPreview(entry.local,entry.result);else toast("The source record is no longer loaded")});
    dialog.querySelector("#markJobReviewed")?.addEventListener("click",()=>apply("review"));
    dialog.querySelector("#applyJobSelected")?.addEventListener("click",()=>apply("selected"));
    dialog.querySelector("#applyJobAll")?.addEventListener("click",()=>apply("all"));
    if(scrollState)requestAnimationFrame(()=>{dialog.scrollTop=scrollState.dialog;const table=dialog.querySelector(".job-change-table-wrap");if(table){table.scrollTop=scrollState.tableTop;table.scrollLeft=scrollState.tableLeft}});
  }

  render();
  if(["queued","running","cancelling"].includes(job.status)){
    liveTimer=setInterval(async()=>{
      if(!dialog.isConnected){clearInterval(liveTimer);return}
      const before=job.completed;
      const pendingBefore=job.pending_result_count;
      if(await refreshJob()){
        if(job.completed!==before||job.pending_result_count!==pendingBefore||!["queued","running","cancelling"].includes(job.status)){
          render({preserveScroll:true});
        }
        if(!["queued","running","cancelling"].includes(job.status)){
          clearInterval(liveTimer);liveTimer=null;
        }
      }
    },4000);
  }
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

async function openRagResult(job){
  if(!job?.id)return toast(tr("research.result_unavailable","This Research run has no result identifier."),{tone:"warn"});
  if(!canAccessPage("rag"))return toast(tr("permissions.research_result_denied","Your role cannot open Research results."),{tone:"warn"});
  // v0.35.5: a RAG result is a research object, not a legacy modal. Open it in
  // the same native result workspace used by Research so typography, source
  // binding, evidence inspection, accessibility, and i18n stay identical no
  // matter where the result was launched (Operations, job history, etc.).
  state.view="rag";
  persistPrefs();
  shellRefreshHook?.();
  const href=`/rag?job=${encodeURIComponent(job.id)}`;
  if(urlSyncHook){urlSyncHook(href,{replace:false,snapshot:navSnapshot()});return}
  location.assign(href);
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

const WORK_METADATA_FIELDS=[
  "work","source_type","document_type","document_title","short_title","original_title","document_author",
  "container_title","journal_title","editor","edition","volume","issue","pages","year","publication_year",
  "publisher","publication_place","translator","document_language","original_language","document_is_translation",
  "canonical_work_id","isbn","doi","url","full_citation","cover_url"
];
function openMixedWorkValuesDialog(work,field,rows){
  const values=uniqueWorkValues(rows,field);
  const dialog=document.createElement("dialog");
  dialog.className="mixed-values-dialog";
  dialog.setAttribute("aria-labelledby","mixedValuesTitle");
  dialog.innerHTML=`<div class="dh"><div><span class="section-label">${esc(tr("works.metadata_variants","Metadata variants"))}</span><h2 class="dialog-title" id="mixedValuesTitle">${esc(label(field))}</h2><div class="dialog-subtitle">${esc(work)} · ${values.length.toLocaleString()} ${esc(tr("works.unique_values","unique values"))} · ${rows.length.toLocaleString()} ${esc(tr("dynamic.records","records"))}</div></div><button class="btn icon-only" type="button" data-close aria-label="${esc(tr("ui.close","Close"))}">${icon("close")}</button></div><div class="db mixed-values-body"><p class="note">${esc(tr("works.mixed_values_help","These are the distinct values currently present across records for this work. Counts help distinguish a dominant value from an isolated inconsistency before you bulk-edit metadata."))}</p><div class="mixed-values-list">${values.map((entry,index)=>`<article class="mixed-value-row"><span class="mixed-value-rank">${index+1}</span><div class="mixed-value-copy"><b>${esc(entry.value==null||entry.value===""?tr("ui.unset","Unset"):display(entry.value))}</b><small>${esc([...entry.files].slice(0,3).join(" · "))}${entry.files.size>3?` · +${entry.files.size-3}`:""}</small></div><span class="mixed-value-count">${entry.count.toLocaleString()} <small>${esc(entry.count===1?tr("dynamic.record_one","record"):tr("dynamic.records","records"))}</small></span></article>`).join("")}</div></div><div class="da"><button class="btn primary" type="button" data-close>${esc(tr("ui.done","Done"))}</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
}
function openWorkMetadataEditor(work,rows){
  if(!rows?.length)return toast("No records found for this work");
  const available=[...new Set([...WORK_METADATA_FIELDS,...rows.flatMap(row=>Object.keys(row.record).filter(field=>/^(document_|publication_|canonical_|publisher$|translator$|isbn$|full_citation$)/.test(field)))])].filter(field=>field!=="updates");
  const dialog=document.createElement("dialog");
  dialog.className="work-metadata-dialog";
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Edit work metadata</h2><div class="dialog-subtitle">${esc(work)} · ${rows.length.toLocaleString()} associated records across ${new Set(rows.map(row=>row.file.name)).size} files</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db work-metadata-body"><div class="info">Check <b>Apply</b> only for fields that should be changed across every associated record. Changing <code>work</code> renames the work for all loaded records. Every modified field is written to each record's <code>updates</code> history.</div><div class="work-meta-table">${available.map(field=>workMetadataControl(field,rows)).join("")}</div></div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="applyWorkMetadata">Apply selected metadata to ${rows.length.toLocaleString()} records</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelectorAll("[data-inspect-mixed-field]").forEach(button=>button.onclick=()=>openMixedWorkValuesDialog(work,button.dataset.inspectMixedField,rows));
  dialog.querySelector("#applyWorkMetadata").onclick=async()=>{
    const selected=[...dialog.querySelectorAll("[data-work-meta-apply]:checked")].map(box=>box.dataset.workMetaApply);
    if(!selected.length)return toast("Select at least one work metadata field to apply");
    const changes={};
    try{
      for(const field of selected){
        const control=dialog.querySelector(`[data-work-meta-value="${CSS.escape(field)}"]`);
        changes[field]=parseWorkMetadataValue(field,control,rows);
      }
    }catch(error){return toast(error.message)}
    if(!await openMessageModal({title:"Apply work metadata?",message:`Apply ${selected.length} metadata field${selected.length===1?"":"s"} to all ${rows.length} records associated with ${work}?`,confirmLabel:"Apply metadata",cancelLabel:"Cancel"}))return;
    const applyButton=dialog.querySelector("#applyWorkMetadata");if(applyButton){applyButton.disabled=true;applyButton.textContent=tr("works.applying_metadata","Applying metadata…")}
    const batchId=uid();let changedRecords=0,fieldChanges=0;const touchedFiles=new Set();
    for(const row of rows){
      const count=applyRecordChanges(row.file,row.index,changes,{source:"work_metadata",batchId,reason:`Bulk work metadata update for ${work}`});
      if(count){changedRecords++;fieldChanges+=count;touchedFiles.add(row.file)}
    }
    for(const file of touchedFiles)await persistFileNow(file);
    close();shell();renderView();
    toast(trf("works.metadata_applied","Updated {records} records · {fields} tracked field changes",{records:changedRecords.toLocaleString(),fields:fieldChanges.toLocaleString()}),{tone:"success"});
  };
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

function openWorkMetadataLlmDialog(items){
  const works=(items||[]).filter(item=>item?.work&&item?.rows?.length);
  if(!works.length)return toast(tr("works.no_work_metadata_rows","No work records are available for metadata lookup."));
  const profiles=providerProfiles();
  const selectedId=state.appConfig.default_provider_profile||profiles[0]?.id||"";
  const dialog=document.createElement("dialog");
  dialog.className="workflow-dialog work-metadata-llm-dialog";
  const sample=works.slice(0,6).map(item=>`<span>${esc(item.work)}</span>`).join("");
  dialog.innerHTML=`<div class="workflow-dialog-header"><div class="workflow-heading"><span class="workflow-icon">${icon("spark")}</span><div><p>${esc(tr("works.metadata_workflow_kicker","Bibliographic enrichment"))}</p><h2>${esc(tr("works.populate_metadata_llm","Populate metadata with LLM"))}</h2><span>${esc(tr("works.populate_metadata_help","DerridAI searches format-appropriate public bibliographic sources (Open Library, Google Books, and Crossref), asks the selected LLM to identify the best match, then returns proposed metadata changes for review. Nothing is applied automatically."))}</span></div></div><button class="icon-btn workflow-close" data-close title="${esc(tr("ui.close","Close"))}">×</button></div>
    <ol class="workflow-steps"><li class="active"><span>1</span><b>${esc(tr("works.step_scope","Works"))}</b></li><li class="active"><span>2</span><b>${esc(tr("works.step_provider","Provider profile"))}</b></li><li><span>3</span><b>${esc(tr("works.step_review","Review proposals"))}</b></li></ol>
    <div class="workflow-form"><section class="workflow-section"><div class="workflow-section-copy"><b>${esc(tr("works.lookup_scope","Lookup scope"))}</b><span>${esc(trf("works.lookup_scope_help","Retrieve bibliographic metadata for {count} work(s).",{count:works.length.toLocaleString()}))}</span></div><div class="work-metadata-scope"><strong>${works.length.toLocaleString()} ${esc(tr("dynamic.works","works"))}</strong><div class="work-metadata-sample">${sample}${works.length>6?`<span>+${works.length-6}</span>`:""}</div><small>${esc(tr("works.metadata_fields_help","Proposals can include source type, container/journal, volume/issue/pages, publisher, year, edition, translator/editor, ISBN/DOI, language, MLA citation, and cover image."))}</small></div></section>
    <section class="workflow-section"><div class="workflow-section-copy"><b>${esc(tr("works.provider_profile","Provider profile"))}</b><span>${esc(tr("works.provider_profile_help","Uses the same configured provider profiles as RAG, PDF tools, and LLM review."))}</span></div><div class="workflow-provider-area">${workflowProviderSelectHtml(selectedId)}<button type="button" class="btn small" id="manageWorkProviders">${esc(tr("language.manage_providers","Manage provider profiles"))}</button></div></section>
    <section class="workflow-review-strip"><span class="workflow-summary-icon">${icon("history")}</span><span><b>${esc(tr("works.background_operation","Background operation"))}</b><small>${esc(tr("works.background_operation_help","You can leave the Works page. Open the completed operation to review and apply proposed changes."))}</small></span><span><b>${esc(tr("works.catalog_source","Catalogue source"))}</b><small>Open Library · Google Books · Crossref</small></span></section></div>
    <div class="workflow-actions"><button class="btn" data-close>${esc(tr("ui.cancel","Cancel"))}</button><button class="btn primary" id="startWorkMetadata" ${profiles.length?"":`disabled data-disabled-reason="${esc(tr("works.no_provider_profiles_help","Create an LLM provider profile before populating work metadata."))}"`}>${icon("spark")}${esc(tr("works.start_metadata_lookup","Start background lookup"))}</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);decorateDisabledControls(dialog);
  const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#workMetadataProvider")?.addEventListener("change",event=>{const profile=providerProfile(event.target.value);const summary=dialog.querySelector("#workMetadataProviderSummary");if(summary)summary.innerHTML=workflowProviderSummaryHtml(profile)});
  dialog.querySelector("#manageWorkProviders")?.addEventListener("click",async()=>{const ok=await openMessageModal({title:tr("works.leave_metadata_title","Open provider profiles?"),message:tr("works.leave_metadata_help","This will close the metadata workflow and navigate to LLM Providers. Your lookup has not started yet."),confirmLabel:tr("works.open_providers","Open providers"),cancelLabel:tr("ui.cancel","Cancel")});if(!ok)return;close();navigateTo("providers")});
  dialog.querySelector("#startWorkMetadata")?.addEventListener("click",async()=>{
    const profileId=dialog.querySelector("#workMetadataProvider")?.value||selectedId;
    const profile=providerProfile(profileId);
    if(!profile)return toast(tr("works.provider_required","Select an LLM provider profile."));
    const config=providerRequestConfig(profile,{textReview:false});
    if(!config?.model)return toast(tr("works.provider_model_required","The selected provider profile does not have a model configured."));
    const payload=works.map(item=>({work:item.work,current_metadata:representativeWorkMetadata(item.rows)}));
    const button=dialog.querySelector("#startWorkMetadata");button.disabled=true;button.textContent=tr("works.starting_metadata_lookup","Starting…");
    try{
      const job=await api("/api/jobs/llm-tool",{method:"POST",body:JSON.stringify({task:"work_metadata",label:works.length===1?`${tr("works.populate_metadata_llm","Populate metadata with LLM")} · ${works[0].work}`:trf("works.populate_all_metadata_label","Populate metadata · {count} works",{count:works.length}),provider_profile_id:profile.id,max_concurrent_requests:config.max_concurrent_requests,work_metadata:{works:payload,provider:config.provider,model:config.model,base_url:config.base_url,api_key:config.api_key,generation:config.ollama,provider_profile_id:profile.id}})});
      state.jobs=[job,...state.jobs.filter(existing=>existing.id!==job.id)];syncJobProgressToasts();startJobPolling();close();toast(trf("works.metadata_lookup_started","Metadata lookup started for {count} work(s).",{count:works.length}));if(state.view==="home")renderDashboard(document.querySelector("#main"));
    }catch(error){button.disabled=false;button.innerHTML=`${icon("spark")}${esc(tr("works.start_metadata_lookup","Start background lookup"))}`;openMessageModal({title:tr("works.metadata_lookup_failed","Could not start metadata lookup"),message:error.message||String(error),tone:"danger"})}
  });
}
function parseProposedMetadataValue(raw,original){
  if(typeof original==="number"){const value=Number(raw);if(!Number.isFinite(value))throw new Error("Expected a number.");return value}
  if(typeof original==="boolean")return String(raw).toLowerCase()==="true";
  return raw;
}
function openWorkMetadataProposalResult(job){
  const proposals=Array.isArray(job.result?.proposals)?job.result.proposals:[];
  const map=workIndex();
  const flattened=[];
  for(const proposal of proposals){
    const item=map.get(String(proposal.work||""));
    if(!item)continue;
    const current=representativeWorkMetadata(item.rows);
    for(const [field,proposed] of Object.entries(proposal.changes||{}))flattened.push({proposal,item,field,current:current[field],proposed,rationale:proposal.rationale?.[field]||proposal.match_reason||""});
  }
  const dialog=document.createElement("dialog");dialog.className="work-metadata-proposal-dialog";
  const errors=proposals.filter(item=>item.error||item.message&&!Object.keys(item.changes||{}).length);
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(tr("works.review_metadata_proposals","Review work metadata proposals"))}</h2><div class="dialog-subtitle">${esc(jobLabel(job))} · ${flattened.length.toLocaleString()} ${esc(tr("works.proposed_field_changes","proposed field changes"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db work-proposal-body">${errors.length?`<div class="info warn">${esc(trf("works.metadata_no_match_count","{count} work(s) had no usable catalogue match or returned an error.",{count:errors.length}))}</div>`:""}<div class="work-proposal-toolbar"><button class="btn small" id="selectAllWorkProposals">${esc(tr("ui.select_all","Select all"))}</button><button class="btn small" id="clearWorkProposals">${esc(tr("ui.clear","Clear"))}</button><span class="note">${esc(tr("works.proposal_edit_help","Edit proposed values if needed, then apply selected fields across every loaded record belonging to that work."))}</span></div>${flattened.length?`<div class="work-proposal-table-wrap"><table class="work-proposal-table"><thead><tr><th></th><th>${esc(tr("nav.works","Work"))}</th><th>${esc(tr("works.field","Field"))}</th><th>${esc(tr("works.current_value","Current"))}</th><th>${esc(tr("works.proposed_value","Proposed"))}</th><th>${esc(tr("works.source_reason","Source / reason"))}</th></tr></thead><tbody>${flattened.map((entry,index)=>`<tr><td><input type="checkbox" data-work-proposal-select="${index}" checked></td><td><b>${esc(entry.item.work)}</b><small>${entry.item.count.toLocaleString()} ${esc(tr("dynamic.records","records"))}</small></td><td>${esc(label(entry.field))}</td><td><div class="proposal-current">${esc(display(entry.current))}</div></td><td><textarea class="control proposal-value" data-work-proposal-value="${index}" rows="2">${esc(entry.proposed==null?"":typeof entry.proposed==="object"?JSON.stringify(entry.proposed):String(entry.proposed))}</textarea></td><td><small>${esc(entry.rationale||tr("works.catalogue_selected","Public bibliographic catalogue match selected by the LLM."))}</small>${entry.proposal.confidence!=null?`<span class="proposal-confidence">${Math.round(Number(entry.proposal.confidence||0)*100)}%</span>`:""}</td></tr>`).join("")}</tbody></table></div>`:`<div class="llm-empty">${esc(tr("works.no_metadata_changes","No metadata changes were proposed."))}</div>`}${errors.length?`<details class="work-proposal-errors"><summary>${esc(tr("works.unmatched_works","Unmatched / failed works"))}</summary>${errors.map(item=>`<div><b>${esc(item.work)}</b><span>${esc(item.error||item.message||tr("works.no_catalogue_match","No catalogue match"))}</span></div>`).join("")}</details>`:""}</div><div class="da"><button class="btn" data-close>${esc(tr("ui.close","Close"))}</button><button class="btn primary" id="applyWorkProposals" ${flattened.length?"":"disabled"}>${icon("check")}${esc(tr("works.apply_selected_metadata","Apply selected metadata"))}</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);decorateDisabledControls(dialog);
  const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#selectAllWorkProposals")?.addEventListener("click",()=>dialog.querySelectorAll("[data-work-proposal-select]").forEach(box=>box.checked=true));
  dialog.querySelector("#clearWorkProposals")?.addEventListener("click",()=>dialog.querySelectorAll("[data-work-proposal-select]").forEach(box=>box.checked=false));
  dialog.querySelector("#applyWorkProposals")?.addEventListener("click",async()=>{
    const selected=[...dialog.querySelectorAll("[data-work-proposal-select]:checked")].map(box=>Number(box.dataset.workProposalSelect)).filter(index=>flattened[index]);
    if(!selected.length)return toast(tr("works.select_metadata_changes","Select at least one proposed metadata change."));
    const grouped=new Map();
    try{
      for(const index of selected){const entry=flattened[index];const control=dialog.querySelector(`[data-work-proposal-value="${index}"]`);const value=parseProposedMetadataValue(control.value,entry.proposed);if(!grouped.has(entry.item.work))grouped.set(entry.item.work,{item:entry.item,changes:{},rationale:{}});const group=grouped.get(entry.item.work);group.changes[entry.field]=value;group.rationale[entry.field]=entry.rationale}
    }catch(error){return toast(error.message)}
    const recordCount=[...grouped.values()].reduce((sum,group)=>sum+group.item.rows.length,0);
    const applyButton=dialog.querySelector("#applyWorkProposals");if(applyButton){applyButton.disabled=true;applyButton.textContent=tr("works.applying_metadata","Applying metadata…")}
    const batchId=uid();let changedRecords=0,fieldChanges=0;const touchedFiles=new Set();
    try{
      for(const group of grouped.values())for(const row of group.item.rows){const count=applyRecordChanges(row.file,row.index,group.changes,{source:"work_metadata_llm",model:job.model,batchId,reason:`LLM-assisted bibliographic metadata update for ${group.item.work}`,rationale:group.rationale});if(count){changedRecords++;fieldChanges+=count;touchedFiles.add(row.file)}}
      for(const file of touchedFiles)await persistFileNow(file);
      state.jobApplied[job.id]=new Date().toISOString();persistPrefs();close();shell();renderView();toast(trf("works.metadata_applied","Updated {records} records · {fields} tracked field changes",{records:changedRecords.toLocaleString(),fields:fieldChanges.toLocaleString()}),{tone:"success"});
    }catch(error){if(applyButton){applyButton.disabled=false;applyButton.textContent=tr("works.apply_selected_metadata","Apply selected metadata")}toast(error.message||String(error),{tone:"danger"})}
  });
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

function openSubsetBuilder(){
  if(!state.files.length)return toast("Load one or more JSONL files first");
  const dialog=document.createElement("dialog");
  dialog.className="subset-dialog";
  const fields=recordFields().filter(field=>!field.startsWith("_"));
  const sourceOptions=[
    `<option value="active">Active JSONL · ${esc(activeFile()?.name||"")}</option>`,
    `<option value="all">All loaded JSONL files</option>`,
    ...state.files.map(file=>`<option value="${esc(file.id)}">Only ${esc(file.name)} · ${file.records.length.toLocaleString()} records</option>`),
  ].join("");
  const fieldOptions=fields.map(field=>`<option value="${esc(field)}">${esc(label(field))} · ${esc(field)}</option>`).join("");
  const operatorOptions=[["equals","Equals"],["not_equals","Does not equal"],["contains","Contains"],["not_contains","Does not contain"],["array_contains","Array contains exact value"],["exists","Exists / non-empty"],["missing","Missing / empty"],["truthy","Truthy"],["falsy","Falsy"],["regex","Regular expression"]].map(([value,name])=>`<option value="${value}">${name}</option>`).join("");
  const profiles=loadSubsetProfiles();
  dialog.innerHTML=`<div class="dh subset-dialog-head"><div><span class="section-label">Corpus utility</span><h2 class="dialog-title">Create JSONL subset</h2><div class="dialog-subtitle">Build reusable record filters without editing the source JSONL.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db subset-body subset-body-v3">
    <section class="subset-config-card"><div class="subset-config-copy"><b>Source & output</b><span>Choose the loaded records to filter and the name of the derived JSONL tab.</span></div><div class="subset-head-grid"><div class="field"><label>Source</label><select class="control" id="subsetSource">${sourceOptions}</select></div><div class="field"><label>New JSONL tab name</label><input class="control" id="subsetName" value="${esc((activeFile()?.name||"subset.jsonl").replace(/\.jsonl$/i,""))}-subset.jsonl"></div><label class="check-item subset-case"><input type="checkbox" id="subsetCase"><span>Case-sensitive matching</span></label></div></section>
    <section class="subset-config-card"><div class="subset-config-copy"><b>Saved filter profile</b><span>Reuse common corpus slices such as primary Derrida text, one language, or records needing review.</span></div><div class="subset-profile-row"><select class="control" id="subsetProfile"><option value="">No saved profile</option>${profiles.map(profile=>`<option value="${esc(profile.id)}">${esc(profile.name)}</option>`).join("")}</select><button class="btn small" id="saveSubsetProfile">${icon("plus")}Save current</button><button class="btn small danger" id="deleteSubsetProfile" disabled>Delete</button></div></section>
    <section class="subset-config-card subset-filter-card"><div class="subset-config-copy"><b>Filter expression</b><span>Conditions are readable, grouped explicitly, and previewed against the selected source as you edit.</span></div><div class="subset-expression" id="subsetExpression"></div><div class="subset-builder-actions"><button class="btn small" id="addSubsetRule">${icon("plus")}Condition</button><button class="btn small" id="addSubsetGroup">${icon("plus")}Group</button><span class="subset-match-count" id="subsetPreview">Add at least one condition.</span></div><div class="subset-expression-preview" id="subsetExpressionPreview"></div></section>
  </div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn" id="createSubsetDownload">Create & download</button><button class="btn primary" id="createSubset">Create subset tab</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  const expression=dialog.querySelector("#subsetExpression");
  let previewTimer=null;
  const schedulePreview=()=>{clearTimeout(previewTimer);previewTimer=setTimeout(updatePreview,120)};

  const subsetAutocompleteExcluded=new Set(["text","extracted_text","extractedText","raw_text","ocr_text"]);
  function ruleHtml({field="work",operator="equals",value=""}={}){
    return `<div class="subset-rule-core"><select class="control subset-field">${fieldOptions}</select><select class="control subset-operator">${operatorOptions}</select><input class="control subset-value" placeholder="${esc(tr("subset.value","Value"))}" autocomplete="off"><datalist class="subset-value-options"></datalist><button class="btn icon-only danger subset-remove" type="button" title="${esc(tr("subset.remove_condition","Remove condition"))}" aria-label="${esc(tr("subset.remove_condition","Remove condition"))}">${icon("close")}</button></div>`;
  }
  function initializeRule(row,{field="work",operator="equals",value=""}={}){
    row.querySelector(".subset-field").value=fields.includes(field)?field:fields[0]||"";
    row.querySelector(".subset-operator").value=operator;
    row.querySelector(".subset-value").value=value;
    const input=row.querySelector(".subset-value"),datalist=row.querySelector(".subset-value-options");
    const listId=`subset-values-${uid()}`;datalist.id=listId;
    const syncSuggestions=()=>{
      const fieldName=row.querySelector(".subset-field").value;
      if(subsetAutocompleteExcluded.has(fieldName)){input.removeAttribute("list");datalist.innerHTML="";input.title=tr("subset.autocomplete_large_field","Autocomplete is disabled for large text fields.");return}
      const values=new Set();
      for(const {record} of selectedRows()){
        const raw=record?.[fieldName];
        const items=Array.isArray(raw)?raw:[raw];
        for(const item of items){if(item===null||item===undefined||typeof item==="object")continue;const text=String(item).trim();if(text)values.add(text)}
      }
      const ordered=[...values].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true,sensitivity:"base"}));
      datalist.innerHTML=ordered.map(option=>`<option value="${esc(option)}"></option>`).join("");
      if(ordered.length){input.setAttribute("list",listId);input.title=trf("subset.autocomplete_count","{count} unique values from the selected JSONL source.",{count:ordered.length.toLocaleString()})}
      else{input.removeAttribute("list");input.title=""}
    };
    const syncValue=()=>{
      const noValue=["exists","missing","truthy","falsy"].includes(row.querySelector(".subset-operator").value);
      input.disabled=noValue;
      input.placeholder=noValue?tr("subset.no_value","No value required"):tr("subset.value","Value");
      if(noValue)input.value="";
      if(noValue)input.removeAttribute("list");else syncSuggestions();
    };
    row.querySelectorAll("select,input").forEach(control=>control.addEventListener("input",()=>{syncValue();schedulePreview()}));
    row.querySelector(".subset-remove").onclick=()=>{
      const group=row.closest(".subset-group");
      row.remove();
      if(group&&!group.querySelector(".subset-group-rules .subset-rule-row"))group.remove();
      normalizeTopJoins();updatePreview();
    };
    syncValue();
  }
  function topJoinHtml(){return `<select class="control subset-join"><option value="AND">AND</option><option value="OR">OR</option></select>`}
  function addTopRule(config={}){
    const item=document.createElement("div");
    item.className="subset-expression-item subset-top-rule";
    item.dataset.kind="rule";
    item.innerHTML=`${topJoinHtml()}<div class="subset-rule-row">${ruleHtml(config)}</div>`;
    expression.appendChild(item);
    initializeRule(item.querySelector(".subset-rule-row"),config);
    item.querySelector(".subset-join").addEventListener("change",schedulePreview);
    normalizeTopJoins();updatePreview();
  }
  function addGroup({mode="OR",rules=null}={}){
    const item=document.createElement("div");
    item.className="subset-expression-item subset-group";
    item.dataset.kind="group";
    item.innerHTML=`${topJoinHtml()}<div class="subset-group-box"><div class="subset-group-head"><div><b>Grouped conditions</b><span>Parentheses: evaluate this block as one boolean value</span></div><div class="tools"><select class="control subset-group-mode"><option value="OR">Match ANY (OR)</option><option value="AND">Match ALL (AND)</option></select><button class="btn tiny" type="button" data-add-group-rule>${icon("plus")}Condition</button><button class="btn tiny danger" type="button" data-remove-group>Remove group</button></div></div><div class="subset-group-rules"></div></div>`;
    expression.appendChild(item);
    item.querySelector(".subset-group-mode").value=mode;
    const list=item.querySelector(".subset-group-rules");
    const addInner=(config={})=>{
      const row=document.createElement("div");row.className="subset-rule-row";row.innerHTML=ruleHtml(config);list.appendChild(row);initializeRule(row,config);updatePreview();
    };
    (rules?.length?rules:[{field:"topics",operator:"array_contains",value:""},{field:"concepts",operator:"array_contains",value:""}]).forEach(addInner);
    item.querySelector("[data-add-group-rule]").onclick=()=>addInner({field:fields.includes("topics")?"topics":fields[0],operator:"contains",value:""});
    item.querySelector("[data-remove-group]").onclick=()=>{item.remove();normalizeTopJoins();updatePreview()};
    item.querySelector(".subset-group-mode").addEventListener("change",schedulePreview);
    item.querySelector(".subset-join").addEventListener("change",schedulePreview);
    normalizeTopJoins();updatePreview();
  }
  function normalizeTopJoins(){
    [...expression.querySelectorAll(":scope > .subset-expression-item")].forEach((item,index)=>{
      const join=item.querySelector(":scope > .subset-join");
      join.disabled=index===0;
      if(index===0)join.value="AND";
    });
  }
  function selectedRows(){
    const source=dialog.querySelector("#subsetSource").value;
    if(source==="all")return allRows();
    if(source==="active"){const file=activeFile();return file?file.records.map((record,index)=>({file,record,index})):[]}
    const file=state.files.find(item=>item.id===source);return file?file.records.map((record,index)=>({file,record,index})):[];
  }
  function readRule(row){return {field:row.querySelector(".subset-field").value,operator:row.querySelector(".subset-operator").value,value:row.querySelector(".subset-value").value}}
  function readExpression(){
    return [...expression.querySelectorAll(":scope > .subset-expression-item")].map((item,index)=>{
      const base={join:index===0?"AND":item.querySelector(":scope > .subset-join").value,type:item.dataset.kind};
      if(item.dataset.kind==="group")return {...base,mode:item.querySelector(".subset-group-mode").value,rules:[...item.querySelectorAll(".subset-group-rules .subset-rule-row")].map(readRule)};
      return {...base,rule:readRule(item.querySelector(".subset-rule-row"))};
    });
  }
  function itemMatches(record,item,caseSensitive){
    if(item.type==="group"){
      const values=item.rules.map(rule=>subsetRuleMatches(record,rule,caseSensitive));
      return item.mode==="AND"?values.every(Boolean):values.some(Boolean);
    }
    return subsetRuleMatches(record,item.rule,caseSensitive);
  }
  function recordMatchesExpression(record,items,caseSensitive){
    if(!items.length)return false;
    const groups=[];let group=[];
    for(const item of items){if(item.join==="OR"&&group.length){groups.push(group);group=[]}group.push(item)}
    if(group.length)groups.push(group);
    return groups.some(itemsInAndGroup=>itemsInAndGroup.every(item=>itemMatches(record,item,caseSensitive)));
  }
  function expressionText(items){
    const oneRule=rule=>`${label(rule.field)} ${dialog.querySelector(`.subset-operator option[value="${CSS.escape(rule.operator)}"]`)?.textContent||rule.operator}${["exists","missing","truthy","falsy"].includes(rule.operator)?"":` “${rule.value}”`}`;
    return items.map((item,index)=>{
      const prefix=index?` ${item.join} `:"";
      if(item.type==="group")return `${prefix}(${item.rules.map(oneRule).join(` ${item.mode} `)})`;
      return `${prefix}${oneRule(item.rule)}`;
    }).join("");
  }
  function matchedRows(){const items=readExpression();if(!items.length)return [];const caseSensitive=dialog.querySelector("#subsetCase").checked;return selectedRows().filter(({record})=>recordMatchesExpression(record,items,caseSensitive))}
  function updatePreview(){
    const items=readExpression(),sourceCount=selectedRows().length,matched=items.length?matchedRows().length:0;
    dialog.querySelector("#subsetPreview").textContent=items.length?`${matched.toLocaleString()} of ${sourceCount.toLocaleString()} source records match`:"Add at least one condition.";
    dialog.querySelector("#subsetExpressionPreview").innerHTML=items.length?`<b>Expression</b><code>${esc(expressionText(items))}</code>`:"";
    decorateDisabledControls(dialog);
  }
  const refreshSubsetSuggestions=()=>expression.querySelectorAll(".subset-rule-row").forEach(row=>row.querySelector(".subset-field")?.dispatchEvent(new Event("input",{bubbles:false})));
  const applyProfile=profile=>{
    expression.innerHTML="";
    for(const item of profile?.expression||[]){
      if(item?.type==="group"){addGroup({mode:item.mode||"OR",rules:item.rules||[]});const added=expression.lastElementChild;if(added&&item.join)added.querySelector(":scope > .subset-join").value=item.join}
      else if(item?.rule){addTopRule(item.rule);const added=expression.lastElementChild;if(added&&item.join)added.querySelector(":scope > .subset-join").value=item.join}
    }
    dialog.querySelector("#subsetCase").checked=Boolean(profile?.caseSensitive);
    normalizeTopJoins();refreshSubsetSuggestions();updatePreview();
  };
  const profileSelect=dialog.querySelector("#subsetProfile");
  profileSelect?.addEventListener("change",()=>{
    const profile=loadSubsetProfiles().find(item=>item.id===profileSelect.value);
    dialog.querySelector("#deleteSubsetProfile").disabled=!profile;
    if(profile)applyProfile(profile);
  });
  dialog.querySelector("#saveSubsetProfile")?.addEventListener("click",async()=>{
    const items=readExpression();if(!items.length)return toast("Add at least one condition before saving a profile");
    const name=prompt("Filter profile name");if(!name?.trim())return;
    const profiles=loadSubsetProfiles();const profile={id:uid(),name:name.trim(),expression:items,caseSensitive:dialog.querySelector("#subsetCase").checked,created_at:new Date().toISOString()};
    profiles.push(profile);saveSubsetProfiles(profiles);
    profileSelect.insertAdjacentHTML("beforeend",`<option value="${esc(profile.id)}">${esc(profile.name)}</option>`);profileSelect.value=profile.id;dialog.querySelector("#deleteSubsetProfile").disabled=false;toast(`Saved filter profile “${profile.name}”`,{tone:"success"});
  });
  dialog.querySelector("#deleteSubsetProfile")?.addEventListener("click",()=>{
    const id=profileSelect.value;if(!id)return;const profiles=loadSubsetProfiles();const profile=profiles.find(item=>item.id===id);saveSubsetProfiles(profiles.filter(item=>item.id!==id));profileSelect.querySelector(`option[value="${CSS.escape(id)}"]`)?.remove();profileSelect.value="";dialog.querySelector("#deleteSubsetProfile").disabled=true;if(profile)toast(`Deleted filter profile “${profile.name}”`);
  });
  dialog.querySelector("#addSubsetRule").onclick=()=>addTopRule({field:fields.includes("work")?"work":fields[0],operator:"equals",value:""});
  dialog.querySelector("#addSubsetGroup").onclick=()=>addGroup();
  dialog.querySelector("#subsetSource")?.addEventListener("change",()=>{refreshSubsetSuggestions();schedulePreview()});
  dialog.querySelector("#subsetCase")?.addEventListener("change",schedulePreview);
  const createSubset=async downloadFile=>{
    const items=readExpression();const rows=matchedRows();if(!items.length)return toast("Add at least one subset condition");if(!rows.length)return toast("No records match the subset expression");
    let name=dialog.querySelector("#subsetName").value.trim()||"subset.jsonl";if(!name.toLowerCase().endsWith(".jsonl"))name+=".jsonl";
    const file={id:uid(),name,records:rows.map(({record})=>cloneAuditValue(record)),errors:[],dirty:new Set(),imported_at:new Date().toISOString(),subset:{created_at:new Date().toISOString(),source:dialog.querySelector("#subsetSource").value,logic:"grouped_boolean_v2",expression:items}};
    state.files.push(file);state.activeFileId=file.id;await persistFileNow(file);
    if(downloadFile){const blob=new Blob([file.records.map(record=>JSON.stringify(record)).join("\n")+"\n"],{type:"application/x-ndjson"});downloadBlob(blob,name)}
    close();navigateTo("list",{fileId:file.id});toast(`Created ${name} with ${file.records.length.toLocaleString()} records`);
  };
  dialog.querySelector("#createSubset").onclick=()=>createSubset(false);
  dialog.querySelector("#createSubsetDownload").onclick=()=>createSubset(true);
  addTopRule({field:fields.includes("document_author")?"document_author":fields[0],operator:"equals",value:"Jacques Derrida"});
}

function openBulkFieldEditor({rows=null,title="Bulk edit one field"}={}){
  if(!state.files.length)return toast("Load JSONL records first");
  const dialog=document.createElement("dialog");
  dialog.className="bulk-field-dialog";
  const fields=recordFields().filter(field=>field!=="updates"&&!field.startsWith("_"));
  const selectedCount=selectedReviewItems().length;
  const activeCount=activeFile()?.records.length||0;
  const currentWork=selectedRecord()?.work||"";
  const fixedRows=Array.isArray(rows)?rows:null;
  const defaultScope=fixedRows?"fixed":selectedCount?"selected":"active";
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">Apply one field value consistently across a selected record set. Every actual change is audited.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db bulk-field-body">
    ${fixedRows?`<div class="info">${fixedRows.length.toLocaleString()} records are in this operation.</div>`:`<div class="field"><label>Target records</label><select class="control" id="bulkFieldScope"><option value="selected" ${defaultScope==="selected"?"selected":""} ${selectedCount?"":"disabled"}>Selected records (${selectedCount.toLocaleString()})</option><option value="active" ${defaultScope==="active"?"selected":""}>Active JSONL (${activeCount.toLocaleString()})</option>${currentWork?`<option value="work">Current work: ${esc(currentWork)}</option>`:""}<option value="all">All loaded records (${allRows().length.toLocaleString()})</option></select></div>`}
    <div class="field"><label>Field</label><select class="control" id="bulkFieldName">${fields.map(field=>`<option value="${esc(field)}">${esc(label(field))} · ${esc(field)}</option>`).join("")}</select></div>
    <div class="field"><label>New value</label><textarea id="bulkFieldValue" spellcheck="false" placeholder="Enter the new value. Arrays/objects use JSON. Enter __NULL__ for null."></textarea><div class="note" id="bulkFieldHint"></div></div>
    <label class="check-item"><input type="checkbox" id="bulkFieldOnlyDifferent" checked><span>Only modify records whose value actually differs</span></label>
  </div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="applyBulkField">${icon("check")}Apply field update</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);

  const currentRows=()=>fixedRows||bulkEditRowsForScope(dialog.querySelector("#bulkFieldScope")?.value||"active");
  let lastHintField="";
  const updateHint=()=>{
    const field=dialog.querySelector("#bulkFieldName").value;
    const target=currentRows();
    const rawValues=target.slice(0,300).map(row=>row.record?.[field]);
    const values=[...new Set(rawValues.map(value=>JSON.stringify(value)))];
    dialog.querySelector("#bulkFieldHint").textContent=`${target.length.toLocaleString()} target records · ${values.length} distinct current value${values.length===1?"":"s"}${values.length>8?" (sampled)":""}`;
    const input=dialog.querySelector("#bulkFieldValue");
    if(values.length===1&&(lastHintField!==field||!input.value.trim())){
      const only=rawValues[0];
      input.value=only===null?"__NULL__":Array.isArray(only)||only&&typeof only==="object"?JSON.stringify(only,null,2):String(only??"");
    }else if(lastHintField!==field&&values.length!==1)input.value="";
    lastHintField=field;
  };
  dialog.querySelector("#bulkFieldScope")?.addEventListener("change",updateHint);
  dialog.querySelector("#bulkFieldName").addEventListener("change",updateHint);
  updateHint();

  dialog.querySelector("#applyBulkField").onclick=async()=>{
    const target=currentRows();
    if(!target.length)return toast("No records are in the selected scope");
    const field=dialog.querySelector("#bulkFieldName").value;
    let value;
    try{value=parseBulkFieldValue(field,dialog.querySelector("#bulkFieldValue").value,target)}
    catch(error){return toast(error.message)}
    const changing=target.filter(row=>!sameValue(row.record?.[field],value));
    if(!changing.length)return toast("Every target record already has that value");
    if(!await openMessageModal({title:"Apply bulk field update?",message:`Set ${field} on ${changing.length.toLocaleString()} record${changing.length===1?"":"s"}?`,confirmLabel:"Apply update",cancelLabel:"Cancel"}))return;
    const batchId=uid();let fieldChanges=0;
    for(const row of changing){
      fieldChanges+=applyRecordChanges(row.file,row.index,{[field]:cloneAuditValue(value)},{
        source:"bulk_field_edit",
        batchId,
        reason:`Bulk edit ${field}`,
      });
    }
    close();shell();renderView();
    toast(`Updated ${field} on ${changing.length.toLocaleString()} records · ${fieldChanges.toLocaleString()} audited changes`);
  };
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

async function openRemoveWorkModal(work,rows){
  const fileCounts=new Map();
  for(const row of rows)fileCounts.set(row.file,(fileCounts.get(row.file)||0)+1);
  const dialog=document.createElement("dialog");
  dialog.className="message-dialog danger remove-work-dialog";
  const dbStore=state.activeStore&&recordStores().some(store=>store.name===state.activeStore)?state.activeStore:"";
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Remove entire work</h2><div class="dialog-subtitle">${esc(work)} · destructive operation</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db remove-work-body"><div class="info warn">Remove every record for this work from selected loaded JSONL files and, optionally, from the selected Chroma collection. Primary collection deletion also removes matching records from its language collections.</div>
    <div class="remove-work-files">${[...fileCounts].map(([file,count])=>`<label class="check-item"><input type="checkbox" data-remove-work-file="${esc(file.id)}" checked><span><b>${esc(file.name)}</b><small>${count.toLocaleString()} matching record${count===1?"":"s"}</small></span></label>`).join("")}</div>
    <label class="check-item"><input type="checkbox" id="removeWorkDb" ${dbStore?"":`disabled data-disabled-reason="Select or create a corpus vector database first." title="Select or create a corpus vector database first."`}><span><b>Also remove from Chroma</b><small>${dbStore?esc(dbStore):"Select a corpus collection first"}</small></span></label></div>
    <div class="da"><button class="btn" data-close>Cancel</button><button class="btn danger" id="confirmRemoveWork">Remove work</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#confirmRemoveWork").onclick=async()=>{
    const fileIds=[...dialog.querySelectorAll("[data-remove-work-file]:checked")].map(input=>input.dataset.removeWorkFile);
    const removeDb=Boolean(dialog.querySelector("#removeWorkDb")?.checked&&dbStore);
    if(!fileIds.length&&!removeDb)return toast("Select at least one JSONL file or the Chroma collection");
    const button=dialog.querySelector("#confirmRemoveWork");button.disabled=true;button.textContent="Removing…";
    let localDeleted=0,dbDeleted=0,mirrored=0;
    try{
      for(const fileId of fileIds){
        const file=state.files.find(item=>item.id===fileId);if(!file)continue;
        const before=file.records.length;
        file.records=file.records.filter(record=>String(record.work||"(Untitled work)")!==work);
        const removed=before-file.records.length;
        if(removed){
          localDeleted+=removed;
          clearFileDerivedState(file.id);
          file.dirty=new Set([file.records.length?0:-1]);
          await persistFileNow(file);
        }
      }
      if(removeDb){
        const result=await api(`/api/stores/${encodeURIComponent(dbStore)}/works/${encodeURIComponent(work)}`,{method:"DELETE"});
        dbDeleted=Number(result.deleted||0);
        mirrored=Object.values(result.mirrored_deletes||{}).reduce((sum,value)=>sum+Number(value||0),0);
        state.storeWorksStore="";
        if(state.storePresence[dbStore])state.storePresence[dbStore]={};
        if(state.storePresenceIds[dbStore])state.storePresenceIds[dbStore]={};
        await refreshStores();
      }
      close();persistPrefs();shell();renderView();
      toast(`Removed “${work}” · ${localDeleted.toLocaleString()} local record${localDeleted===1?"":"s"}${removeDb?` · ${dbDeleted.toLocaleString()} DB${mirrored?` · ${mirrored.toLocaleString()} language mirror`:""}`:""}`);
    }catch(error){button.disabled=false;button.textContent="Remove work";openMessageModal({title:"Could not remove work",message:error.message,tone:"danger"})}
  };
}

async function openSeparateWorksModal(){
  const eligible=state.files.filter(file=>{const works=new Set(file.records.map(record=>String(record?.work||record?.document_title||"").trim()).filter(Boolean));return works.size>1});
  if(!eligible.length)return toast("No loaded JSONL file contains multiple named works");
  const dialog=document.createElement("dialog");dialog.className="work-separate-dialog";
  const options=eligible.map(file=>`<option value="${esc(file.id)}">${esc(file.name)} · ${file.records.length.toLocaleString()} records</option>`).join("");
  dialog.innerHTML=`<div class="dh"><div><span class="section-label">JSONL organization</span><h2 class="dialog-title">Separate works from a JSONL file</h2><div class="dialog-subtitle">Create one derived JSONL tab per selected work while preserving record metadata and audit history.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db separate-works-body"><div class="field"><label>Source JSONL</label><select class="control" id="separateWorksSource">${options}</select></div><div id="separateWorksList" class="separate-works-list"></div><label class="check-item"><input type="checkbox" id="separateWorksRemove"><span>Remove separated records from the source tab after creating the new tabs</span></label><div class="info">By default this is non-destructive: new tabs are created as copies. Enable removal only when you want to partition the original loaded JSONL.</div></div><div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="separateWorksCreate">Separate selected works</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  const source=()=>state.files.find(file=>file.id===dialog.querySelector("#separateWorksSource").value);
  const renderList=()=>{const file=source();const groups=new Map();for(const record of file?.records||[]){const work=String(record?.work||record?.document_title||"").trim()||"(Untitled work)";if(!groups.has(work))groups.set(work,[]);groups.get(work).push(record)}dialog.querySelector("#separateWorksList").innerHTML=[...groups.entries()].map(([work,records])=>`<label class="separate-work-row"><input type="checkbox" data-separate-work="${esc(work)}" ${work==="(Untitled work)"?"":"checked"}><span><b>${esc(work)}</b><small>${records.length.toLocaleString()} records</small></span></label>`).join("")};
  dialog.querySelector("#separateWorksSource").addEventListener("change",renderList);renderList();
  dialog.querySelector("#separateWorksCreate").onclick=async()=>{const file=source();const selected=[...dialog.querySelectorAll("[data-separate-work]:checked")].map(box=>box.dataset.separateWork);if(!selected.length)return toast("Select at least one work");const selectedSet=new Set(selected);const created=[];for(const work of selected){const records=file.records.filter(record=>(String(record?.work||record?.document_title||"").trim()||"(Untitled work)")===work).map(cloneAuditValue);if(!records.length)continue;const stem=work.replace(/[^a-z0-9]+/gi,"-").replace(/^-|-$/g,"").slice(0,80)||"untitled-work";const derived={id:uid(),name:`${stem}.jsonl`,records,errors:[],dirty:new Set(),imported_at:new Date().toISOString(),derived_from:{type:"work_separation",source_file:file.name,work}};state.files.push(derived);await persistFileNow(derived);created.push(derived)}if(dialog.querySelector("#separateWorksRemove").checked){file.records=file.records.filter(record=>!selectedSet.has(String(record?.work||record?.document_title||"").trim()||"(Untitled work)"));file.dirty=new Set(file.records.map((_,index)=>index));await persistFileNow(file)}if(created.length)state.activeFileId=created[0].id;close();corpusCache.fields=null;persistPrefs();shell();renderView();toast(`Created ${created.length} work JSONL tab${created.length===1?"":"s"}`,{tone:"success"})};
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
function openOcrCleanupDialog(){
  if(!state.files.length)return toast("Load JSONL records first");
  const dialog=document.createElement("dialog");
  const selected=selectedReviewItems();
  const active=activeFile();
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Clean OCR Artifacts</h2><div class="dialog-subtitle">Conservative ligature, zero-width character, and broken line-hyphen cleanup. No paraphrasing.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db ocr-clean-options"><button class="scope-card" data-scope="active" ${active?"":"disabled"}><b>Active JSONL tab</b><span>${active?`${active.records.length.toLocaleString()} records · ${esc(active.name)}`:"No active tab"}</span></button><button class="scope-card" data-scope="selected" ${selected.length?"":"disabled"}><b>Selected records</b><span>${selected.length.toLocaleString()} currently selected</span></button><button class="scope-card" data-scope="review"><b>Needs-review records</b><span>${needsReviewItems().length.toLocaleString()} flagged records</span></button><button class="scope-card" data-scope="all"><b>All loaded records</b><span>${allRows().length.toLocaleString()} records across ${state.files.length} tabs</span></button></div><div class="da"><button class="btn" data-close>Cancel</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelectorAll("[data-scope]").forEach(button=>button.onclick=async()=>{
    let rows=[];
    if(button.dataset.scope==="active"&&active)rows=active.records.map((record,index)=>({file:active,record,index}));
    else if(button.dataset.scope==="selected")rows=selected.map(item=>({file:item.file,record:item.record,index:item.index}));
    else if(button.dataset.scope==="review")rows=needsReviewItems().map(item=>({file:item.file,record:item.record,index:item.index}));
    else rows=allRows();
    if(!rows.length)return toast("No records in that scope");
    close();
    if(await openMessageModal({title:"Run OCR cleanup?",message:`Run conservative OCR cleanup on ${rows.length.toLocaleString()} records?`,confirmLabel:"Run cleanup",cancelLabel:"Cancel"}))cleanRows(rows);
  });
}


const EDITOR_GROUPS = [
  {name:"Source", fields:["record_id","work","document_author","edition","year","page_start","page_end","region_type","region_author","primary_text","canonical_work_id","pdf_file","pdf_pages"]},
  {name:"Discourse", fields:["speaker","position_holder","target","discourse_role","proposition_status","semantic_function","stance","claim_scope"]},
  {name:"Quotation provenance", fields:["is_direct_quote","quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent","quotation_chain"]},
  {name:"Indexing", fields:["topics","concepts","persons","works_referenced"]},
  {name:"Quality / review", fields:["attribution_confidence","semantic_classification_confidence","extraction_quality","needs_review","review_reason"]},
  {name:"Language / translation", fields:["document_language","original_language","document_is_translation","translator"]},
  {name:"Citation", fields:["inline_citation","full_citation"]},
  {name:"Text", fields:["text","text_length"]},
];

function openEditor(){
  const f=activeFile(),i=selectedIndex(f),r=selectedRecord();if(!r)return;
  const dialog=document.createElement("dialog");
  const used=new Set();
  const groups=[];
  for(const group of EDITOR_GROUPS){
    const fields=group.fields.filter(k=>k in r);
    if(!fields.length)continue;
    fields.forEach(k=>used.add(k));
    groups.push(`<section class="editor-section"><h3>${esc(group.name)}</h3><div class="editor-grid">${fields.map(k=>fieldEditor(k,r[k])).join("")}</div></section>`);
  }
  const other=Object.keys(r).filter(k=>!used.has(k) && k!=="updates");
  if(other.length)groups.push(`<section class="editor-section"><h3>Other fields</h3><div class="editor-grid">${other.map(k=>fieldEditor(k,r[k])).join("")}</div></section>`);
  dialog.innerHTML=`<form><div class="dh"><div><h2 class="dialog-title">Edit record</h2><div class="dialog-subtitle">${esc(r.record_id||"")} · ${esc(r.work||f.name)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body">${groups.join("")}</div><div class="da"><div class="llm-footer-note">Changes stay local until you export or upsert them.</div><button class="btn" type="button" data-close>Cancel</button><button class="btn primary">${icon("check")}Save changes</button></div></form>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  dialog.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>{dialog.close();dialog.remove()});
  dialog.querySelector("form").onsubmit=e=>{
    e.preventDefault();
    const next={...r};
    try{
      dialog.querySelectorAll("[data-key]").forEach(el=>next[el.dataset.key]=parseEditor(el));
    }catch(error){
      openMessageModal({title:"Could not save record",message:error.message,tone:"danger"});return;
    }
    if("text_length" in next)next.text_length=String(next.text||"").length;
    const changes={};
    for(const [field,value] of Object.entries(next))if(field!=="updates"&&!sameValue(r[field],value))changes[field]=value;
    const count=applyRecordChanges(f,i,changes,{source:"manual"});
    dialog.close();dialog.remove();shell();renderView();count?toast(`Saved ${count} tracked change${count===1?"":"s"}`,{tone:"success"}):toast("No changes to save");
  };
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
function openLlmTaskLauncher({
  task,
  title,
  description="",
  contextText="",
  payload={},
  generationProvider=null,
  generationModel=null,
  onForegroundResult=null,
}={}){
  const profiles=providerProfiles();
  if(!profiles.length)return toast("Configure an LLM provider first");
  let profileId=state.appConfig.default_provider_profile||profiles[0].id;
  if(task==="rag_grade"&&generationModel){
    const independent=profiles.find(item=>!(item.type===generationProvider&&String(item.model||"")===String(generationModel)));
    if(independent)profileId=independent.id;
  }
  let runMode=task==="rag_grade_batch"?"background":(isResearcher()?"foreground":"background");
  const dialog=document.createElement("dialog");
  dialog.className="llm-tool-launcher";

  const render=()=>{
    const profile=providerProfile(profileId);
    const status=state.providerStatuses?.[profile.id]||{};
    const sameModel=Boolean(
      generationModel
      && String(profile.model||"")===String(generationModel)
      && (!generationProvider||profile.type===generationProvider)
    );
    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">${esc(description)}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db llm-tool-body">
      ${contextText?`<section class="llm-tool-context"><span>Question / prompt</span><p>${esc(contextText)}</p></section>`:""}
      ${sameModel?`<div class="info warn"><b>Same-model grading warning.</b> This provider/model was also used to generate the RAG answer. Self-grading can be systematically biased; use a different model for a more independent evaluation.</div>`:""}
      <div class="llm-tool-grid">
        <div class="field field-wide"><label>Provider profile</label><select class="control" id="toolProvider">${profiles.map(item=>`<option value="${esc(item.id)}" ${item.id===profile.id?"selected":""}>${esc(providerDisplayName(item))} · ${item.type==="ollama"?"Ollama":"OpenAI-compatible"}</option>`).join("")}</select></div>
        <div class="field"><label>Run mode</label><select class="control" id="toolRunMode" ${isResearcher()||task==="rag_grade_batch"?"disabled":""}>${task==="rag_grade_batch"?'<option value="background" selected>Background operation</option>':isResearcher()?'<option value="foreground" selected>Interactive foreground</option>':`<option value="background" ${runMode==="background"?"selected":""}>Background operation</option><option value="foreground" ${runMode==="foreground"?"selected":""}>Interactive foreground</option>`}</select></div>
        <div class="field field-wide"><label>Model</label><input class="control" id="toolModel" value="${esc(profile.type==="openai"&&profile.model_mode==="auto"?"auto":profile.model||"")}" ${profile.type==="openai"&&profile.model_mode==="auto"?"disabled":""}></div>
        <div class="field"><label>Max concurrent requests</label><input class="control" value="${esc(profile.max_concurrent_requests??1)}" disabled></div>
        ${profile.type==="ollama"?`<div class="field"><label>Context</label><input class="control" id="toolCtx" type="number" value="${esc(profile.num_ctx??16384)}"></div><div class="field"><label>Think</label><select class="control" id="toolThink">${[["false","Off"],["true","On"],["low","Low"],["medium","Medium"],["high","High"]].map(([v,l])=>`<option value="${v}" ${String(profile.think??"false")===v?"selected":""}>${l}</option>`).join("")}</select></div>`:""}
        <div class="field"><label>Max output tokens</label><input class="control" id="toolPredict" type="number" value="${esc(profile.num_predict??4096)}"></div>
        <div class="field"><label>Temperature</label><input class="control" id="toolTemp" type="number" step="0.01" value="${esc(profile.temperature??0)}"></div>
        <div class="field"><label>top_p</label><input class="control" id="toolTopP" type="number" step="0.01" value="${esc(profile.top_p??1)}"></div>
        <div class="field"><label>Seed</label><input class="control" id="toolSeed" type="number" value="${esc(profile.seed??"")}"></div>
        <div class="field field-wide"><label>Advanced options JSON</label><textarea id="toolExtra" spellcheck="false">${esc(profile.extra_options||"{}")}</textarea></div>
      </div>
      <div class="tools llm-tool-profile-actions"><button class="btn small" id="toolWarm">${icon("spark")}Warm this provider</button>${isResearcher()?"":`<button class="btn small" id="toolProviders">${icon("gear")}Manage providers</button>`}<span class="note" id="toolStatus">${status.available?"Endpoint ready":status.error||"Not verified"}</span></div>
    </div>
    <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="runLlmTask">${icon("spark")}${runMode==="background"?"Start background operation":"Run now"}</button></div>`;
    const close=()=>{dialog.close();dialog.remove()};
    dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
    dialog.querySelector("#toolProvider").onchange=e=>{profileId=e.target.value;render()};
    dialog.querySelector("#toolRunMode").onchange=e=>{runMode=e.target.value;render()};
    dialog.querySelector("#toolProviders")?.addEventListener("click",()=>{close();navigateTo("providers")});
    dialog.querySelector("#toolWarm").onclick=async()=>{const el=dialog.querySelector("#toolStatus");el.textContent="Warming…";await warmupProviderProfile(profileId);el.textContent=state.providerWarmups?.[profileId]?.message||"Warmup requested"};
    dialog.querySelector("#runLlmTask").onclick=async()=>{
      const active=providerProfile(profileId);
      if(!active)return toast("Choose an available provider profile before continuing.");
      if(!["ollama","openai"].includes(String(active.type||"")))return toast("The selected provider profile is not supported by this operation.");
      const config=providerRequestConfig(active,{textReview:true});
      let extra={};
      try{extra=JSON.parse(dialog.querySelector("#toolExtra").value||"{}");if(!extra||Array.isArray(extra)||typeof extra!=="object")throw new Error("Advanced options must be an object")}
      catch(error){return toast(error.message)}
      const n=id=>{const raw=dialog.querySelector(`#${id}`)?.value;if(raw===""||raw==null)return null;const value=Number(raw);return Number.isFinite(value)?value:null};
      let think=false;
      if(active.type==="ollama"){const raw=dialog.querySelector("#toolThink")?.value||"false";think=raw==="true"?true:["low","medium","high"].includes(raw)?raw:false}
      const generation=sanitizeResearchGeneration({...config.ollama,num_ctx:active.type==="ollama"?n("toolCtx"):null,num_predict:n("toolPredict")??4096,think,temperature:n("toolTemp")??0,top_p:n("toolTopP")??1,seed:n("toolSeed"),extra_options:extra});
      const model=active.type==="openai"&&active.model_mode==="auto"?"auto":String(dialog.querySelector("#toolModel")?.value||"").trim();
      if(!model)return toast("Select a model before continuing.");
      if(task==="rag_grade"&&(!String(payload.question||"").trim()||!String(payload.answer||"").trim()))return toast("A completed Research question and answer are required before grading.");
      const direct={...payload,provider:active.type,model,base_url:active.base_url||null,api_key:active.type==="openai"?active.api_key||"":null,generation};
      const button=dialog.querySelector("#runLlmTask");button.disabled=true;button.textContent=runMode==="background"?"Starting…":"Running…";
      try{
        if(runMode==="background"){
          const body={task,label:title,provider_profile_id:active.id,max_concurrent_requests:Math.max(1,Math.min(64,Number(active.max_concurrent_requests)||1)),pdf:task.startsWith("pdf_")?direct:null,grade:task==="rag_grade"?direct:null,grade_batch:task==="rag_grade_batch"?{provider:direct.provider,model:direct.model,base_url:direct.base_url,api_key:direct.api_key,generation:direct.generation,provider_profile_id:active.id,max_concurrent_requests:Math.max(1,Math.min(64,Number(active.max_concurrent_requests)||1))}:null};
          const job=await api("/api/jobs/llm-tool",{method:"POST",body:JSON.stringify(body)});
          state.jobs=[job,...state.jobs.filter(item=>item.id!==job.id)];syncJobProgressToasts();startJobPolling();close();toast(`${title} started in background`);
        }else{
          if(task==="rag_grade_batch")throw new Error("Cache-wide grading runs as a background operation.");
          const endpoint=task==="rag_grade"?"/api/rag/grade":"/api/pdf/llm";
          const result=await api(endpoint,{method:"POST",body:JSON.stringify(direct)});
          close();if(onForegroundResult)await onForegroundResult(result);
        }
      }catch(error){button.disabled=false;button.innerHTML=`${icon("spark")}${runMode==="background"?"Start background operation":"Run now"}`;toast(`${title} failed: ${error.message}`)}
    };
  };
  document.body.appendChild(dialog);showAppModal(dialog);render();
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
function openLlmToolResult(job){
  const result=job.result;
  if(!result)return openMessageModal({title:"Result unavailable",message:"This completed LLM operation does not contain a retained result. Open full details to inspect the operation.",tone:"danger"});
  const dialog=document.createElement("dialog");
  dialog.className="llm-tool-result-dialog";
  const task=job.tool||job.mode;
  if(task==="work_metadata"){dialog.remove();return openWorkMetadataProposalResult(job)}
  let body="",actions="";
  if(task==="pdf_clean_text"){body=`<section class="card-inset"><div class="cardhead"><b>Cleaned page text</b></div><pre class="llm-tool-text">${esc(result.text||"")}</pre></section>`;actions='<button class="btn primary" id="useToolText">Use as current page text</button>'}
  else if(task==="pdf_draft_record"){body=`<pre class="rag-json">${esc(JSON.stringify(result.record||{},null,2))}</pre>`;actions='<button class="btn primary" id="openToolDraft">Review / add draft</button>'}
  else if(task==="pdf_link_record"){body=`<div class="llm-tool-match"><b>${esc(result.match?.record_id||"No supported match")}</b><p>${esc(result.match?.reason||"")}</p></div>`;actions=result.match?.key?'<button class="btn primary" id="applyToolLink">Review & link page</button>':""}
  else if(task==="rag_grade"){
    const question=job.request?.question||"";
    body=`${question?`<section class="llm-tool-context"><span>Question / prompt</span><p>${esc(question)}</p></section>`:""}${result.response_cache_error?`<div class="info warn">The grade completed, but saving it to the response cache failed: ${esc(result.response_cache_error)}</div>`:""}${ragGradeHtml(result.grade||{})}`;
  }
  else if(task==="rag_grade_batch"){
    body=`<section class="bulk-grade-result"><div class="compare-result-summary"><div><strong>${Number(result.graded||0).toLocaleString()}</strong><span>graded</span></div><div><strong>${Number(result.failed||0).toLocaleString()}</strong><span>failed</span></div><div><strong>${Number(result.total||0).toLocaleString()}</strong><span>responses</span></div></div>${Array.isArray(result.errors)&&result.errors.length?`<details><summary>Errors (${result.errors.length})</summary><pre class="rag-json">${esc(JSON.stringify(result.errors,null,2))}</pre></details>`:'<div class="info">All cached responses were processed.</div>'}</section>`;
  }
  else body=`<pre class="rag-json">${esc(JSON.stringify(result,null,2))}</pre>`;
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(jobLabel(job))}</h2><div class="dialog-subtitle">${esc(job.provider||"")} · ${esc(job.model||result.model||"")}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db">${body}</div><div class="da"><button class="btn" data-close>Close</button>${actions}</div>`;
  document.body.appendChild(dialog);const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);showAppModal(dialog);
  dialog.querySelector("#useToolText")?.addEventListener("click",()=>{state.pdf.text=result.text||"";state.pdf.extractionSource=`LLM cleanup · ${job.model||result.model||"model"}`;close();if(state.view==="pdf")renderPdf(document.querySelector("#main"))});
  dialog.querySelector("#openToolDraft")?.addEventListener("click",()=>{close();openPdfDraftRecord(result.record||{})});
  dialog.querySelector("#applyToolLink")?.addEventListener("click",async()=>{await applyPdfLinkMatch(result.match||{});close()});
}
function ragGradeHtml(grade={}){
  const normalized=normalizeRagGrade(grade);
  const scoreKeys=[["query_relevance","Query relevance"],["source_binding","Source binding"],["claim_traceability","Claim traceability"],["attribution_source_discrimination","Attribution/source discrimination"],["claim_evidence_fidelity","Claim/evidence fidelity"],["conceptual_precision","Conceptual precision"],["coverage","Coverage"],["interpretive_usefulness","Interpretive usefulness"],["overall","Overall"]];
  const sections=[["Strengths",normalized.strengths],["Weaknesses",normalized.weaknesses],["Unsupported or risky claims",normalized.unsupported_or_risky_claims]];
  return `<div class="rag-grade-content"><div class="rag-grade-scores">${scoreKeys.map(([key,name])=>`<div><span>${esc(name)}</span><strong>${esc(normalized.score(key))}</strong><small>/10</small></div>`).join("")}</div><section><b>Summary</b><p>${esc(normalized.summary||"No summary returned.")}</p></section>${sections.map(([name,items])=>`<section><b>${esc(name)}</b><ul>${items.map(item=>`<li>${esc(item)}</li>`).join("")||"<li>None reported.</li>"}</ul></section>`).join("")}</div>`;
}

function openPdfDraftRecord(record){
  const dialog=document.createElement("dialog");
  dialog.className="pdf-draft-dialog";
  const files=state.files;
  const stores=recordStores();
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Draft record from PDF page</h2><div class="dialog-subtitle">${esc(state.pdf.title||state.pdf.name)} · page ${state.pdf.page} · unsaved draft</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db pdf-draft-body">
    <div class="info warn">This is a draft generated by an LLM. Review attribution, page metadata, quotation provenance, and text before saving.</div>
    <textarea class="pdf-draft-json" id="pdfDraftJson" spellcheck="false">${esc(JSON.stringify(record,null,2))}</textarea>
    <div class="pdf-draft-targets">
      <div class="field"><label>JSONL destination</label><select class="control" id="pdfDraftFile"><option value="">Do not add to JSONL</option>${files.map(file=>`<option value="${esc(file.id)}">${esc(file.name)} · ${file.records.length} records</option>`).join("")}</select></div>
      <div class="field"><label>Chroma destination</label><select class="control" id="pdfDraftStore" ${stores.length?"":`disabled data-disabled-reason="Create or restore a corpus vector database before upserting PDF drafts." title="Create or restore a corpus vector database before upserting PDF drafts."`}><option value="">${stores.length?"Do not upsert to Chroma":"No corpus database available"}</option>${stores.map(store=>`<option value="${esc(store.name)}">${esc(store.name)} · ${Number(store.count||0).toLocaleString()} records</option>`).join("")}</select></div>
    </div>
  </div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="savePdfDraft">${icon("check")}Add draft</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#savePdfDraft").onclick=async()=>{
    let draft;
    try{
      draft=JSON.parse(dialog.querySelector("#pdfDraftJson").value);
      if(!draft||typeof draft!=="object"||Array.isArray(draft))throw new Error("Draft must be one JSON object.");
    }catch(error){return toast(`Invalid draft JSON: ${error.message}`)}
    if(!draft.record_id)draft.record_id=`pdf-draft-${Date.now()}`;
    draft.needs_review=true;
    draft.updates=Array.isArray(draft.updates)?draft.updates:[];
    draft.pdf_file=state.pdf.name||draft.pdf_file||null;
    draft.pdf_pages=[...new Set([...(Array.isArray(draft.pdf_pages)?draft.pdf_pages:[]),state.pdf.page])].sort((a,b)=>a-b);
    draft.text_length=String(draft.text||"").length;

    const fileId=dialog.querySelector("#pdfDraftFile").value;
    const storeName=dialog.querySelector("#pdfDraftStore").value;
    if(!fileId&&!storeName)return toast("Choose a JSONL file, a Chroma collection, or both.");

    if(fileId){
      const file=state.files.find(item=>item.id===fileId);
      if(!file)return toast("Selected JSONL file is no longer loaded");
      file.records.push(cloneAuditValue(draft));
      file.dirty.add(file.records.length-1);
      await persistFileNow(file);
    }
    if(storeName){
      try{
        await api(`/api/stores/${encodeURIComponent(storeName)}/records`,{
          method:"POST",
          body:JSON.stringify({record:upsertRecordPayload(draft)}),
        });
        await refreshStores();
      }catch(error){
        return toast(`Draft was added to JSONL where selected, but Chroma upsert failed: ${error.message}`);
      }
    }
    close();shell();renderView();
    toast(`Draft ${draft.record_id} added${fileId&&storeName?" to JSONL and Chroma":fileId?" to JSONL":" to Chroma"}`,{tone:"success"});
  };
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
function openStoreRecordEditor(record){
  const chromaId=record._chroma_id;
  if(!chromaId)return toast(tr("record.no_storage_id","This Chroma record has no storage ID"));
  const dialog=document.createElement("dialog");
  const editable=Object.keys(record).filter(k=>k!=="_chroma_id"&&k!=="updates"&&k!=="_updates_count"&&!k.startsWith("_researcher_"));
  dialog.innerHTML=`<form><div class="dh"><div><h2 class="dialog-title">Edit Chroma record</h2><div class="dialog-subtitle">${esc(chromaId)} · ${esc(state.activeStore)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body"><div class="info">Saving updates this record in place under the same Chroma ID and regenerates its embedding when the configured embedding provider allows it.</div><section class="editor-section"><h3>Record</h3><div class="editor-grid">${editable.map(k=>fieldEditor(k,record[k])).join("")}</div></section></div><div class="da"><button class="btn" type="button" data-close>Cancel</button><button class="btn primary">${icon("check")}Save to Chroma</button></div></form>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(b=>b.onclick=close);
  dialog.querySelector("form").onsubmit=async e=>{
    e.preventDefault();
    const raw={...record};delete raw._chroma_id;
    const changes={};
    try{
      dialog.querySelectorAll("[data-key]").forEach(el=>{
        const value=parseEditor(el);
        if(!sameValue(raw[el.dataset.key],value))changes[el.dataset.key]=value;
      });
    }catch(error){openMessageModal({title:"Could not parse edited record",message:error.message,tone:"danger"});return}
    if(!Object.keys(changes).length)return close();
    const timestamp=new Date().toISOString(),batchId=uid();
    const auditEntries=Object.entries(changes).map(([field,newValue])=>({
      field_name:field,old_value:cloneAuditValue(raw[field]),new_value:cloneAuditValue(newValue),timestamp,
      source:"chroma_manual",batch_id:batchId,initiated_by:state.userContext?.username||null,
    }));
    try{
      await api(`/api/stores/${encodeURIComponent(state.activeStore)}/records/${encodeURIComponent(chromaId)}`,{
        method:"PATCH",body:JSON.stringify({changes,audit_entries:auditEntries,document_field:"text",embedding_field:"embedding"}),
      });
      state.storeWorksStore="";
      close();toast("Chroma record updated",{tone:"success"});renderView();
    }catch(error){toast(`Chroma update failed: ${error.message}`,{tone:"danger"})}
  };
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
function openTouchup(inputItems=null,initialMode="foreground"){
  const items=normalizeTouchupItems(inputItems);
  if(!items.length)return;
  window.dispatchEvent(new CustomEvent("derridai:open-touchup",{detail:{items,initialMode}}));
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
