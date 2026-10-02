<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  corpusBuilderApi,
  type CorpusBuild,
  type CorpusRecord,
  type SourceBlock,
  type AutonomousPolicy,
} from "../api/corpus";
import { useI18nStore } from "../stores/i18n";
import DocumentStructureConfigurator from "./DocumentStructureConfigurator.vue";
import MediaStructureConfigurator from "./MediaStructureConfigurator.vue";
import SourceTranscriptionDialog from "./SourceTranscriptionDialog.vue";
import DocumentManifestDialog from "./DocumentManifestDialog.vue";
import CorpusSetupDocumentMetadata from "./corpus-builder/CorpusSetupDocumentMetadata.vue";
import CorpusInitializationDialog from "./CorpusInitializationDialog.vue";
import CorpusBuildReadiness from "./CorpusBuildReadiness.vue";
import CorpusSourceIngest from "./CorpusSourceIngest.vue";
import CorpusRecordSizingSettings from "./CorpusRecordSizingSettings.vue";
import CorpusRecordFocusReview from "./CorpusRecordFocusReview.vue";
import type { CorpusTopologyPolicy, ReviewQueue } from "../types/corpus";
import CorpusMetadataResolutionPanel from "./CorpusMetadataResolutionPanel.vue";
import CorpusSourceQualityDialog from "./CorpusSourceQualityDialog.vue";
import CorpusTextCleanupDialog from "./CorpusTextCleanupDialog.vue";
import CorpusEditorialMemoryDialog from "./CorpusEditorialMemoryDialog.vue";
import CorpusJsonlPreviewDialog from "./CorpusJsonlPreviewDialog.vue";
import CorpusLlmTextTouchupDialog from "./CorpusLlmTextTouchupDialog.vue";
import CorpusBoundarySliceDialog from "./CorpusBoundarySliceDialog.vue";
import CorpusEvidenceBrowserDialog from "./corpus-builder/CorpusEvidenceBrowserDialog.vue";
import MetadataEnrichmentDialog from "./MetadataEnrichmentDialog.vue";
import CorpusHandsFreeSettings from "./CorpusHandsFreeSettings.vue";
import MetadataSchemaEditor from "./MetadataSchemaEditor.vue";
import {
  metadataSchemasApi,
  type MetadataSchema,
  type SchemaSummary,
} from "../api/metadataSchemas";
import UiDialog from "./ui/UiDialog.vue";
import UiButton from "./ui/UiButton.vue";
import { useCorpusBuildLifecycle } from "../composables/useCorpusBuildLifecycle";
import { usePdfCorpusPaneSizing } from "../composables/usePdfCorpusPaneSizing";
import { useCorpusIngestWarning } from "../composables/useCorpusIngestWarning";
import { useCorpusRunGuidance } from "../composables/useCorpusRunGuidance";
import { useCorpusReviewWorkspace } from "../features/corpus-builder/composables/useCorpusReviewWorkspace";
import { useCorpusSourceConfiguration } from "../features/corpus-builder/composables/useCorpusSourceConfiguration";
import { useCorpusProviderConfiguration } from "../features/corpus-builder/composables/useCorpusProviderConfiguration";
import { useCorpusBuildLifecycleController } from "../features/corpus-builder/composables/useCorpusBuildLifecycleController";
import { useCorpusReviewNavigation } from "../features/corpus-builder/composables/useCorpusReviewNavigation";
import {
  useCorpusReviewRecords,
  type ReviewTarget,
} from "../features/corpus-builder/composables/useCorpusReviewRecords";
import type { CorpusQueueRow } from "../features/corpus-builder/api/reviewReads";
import { rowHasSourceWarning } from "../features/corpus-builder/domain/queueRows";
import { useCorpusReviewDecisions } from "../features/corpus-builder/composables/useCorpusReviewDecisions";
import { useCorpusTextReview } from "../features/corpus-builder/composables/useCorpusTextReview";
import { useCorpusMetadataReview } from "../features/corpus-builder/composables/useCorpusMetadataReview";
import { useCorpusBoundaryReview } from "../features/corpus-builder/composables/useCorpusBoundaryReview";
import { invalidRecordSizingFields } from "../features/corpus-builder/domain/recordSizing";
import { corpusReviewCommandFromKeydown } from "../features/corpus-builder/domain/reviewCommands";
import { syncedReviewQuery } from "../features/corpus-builder/domain/workspace";
import {
  editableRecordMetadata,
  evidenceCandidateFieldNames,
  reviewableMetadataFieldNames,
} from "../features/corpus-builder/domain/recordMetadata";
import { useCorpusPublication } from "../features/corpus-builder/composables/useCorpusPublication";
import UiNoticeStack, { type Notice } from "./ui/UiNoticeStack.vue";
import CorpusBuilderWorkspaceHeader from "./corpus-builder/CorpusBuilderWorkspaceHeader.vue";
import CorpusBuildHistoryMenu from "./CorpusBuildHistoryMenu.vue";
import CorpusSetupWorkspace from "./corpus-builder/CorpusSetupWorkspace.vue";
import CorpusBuildWorkspace from "./corpus-builder/CorpusBuildWorkspace.vue";
import CorpusReviewWorkspace from "./corpus-builder/CorpusReviewWorkspace.vue";
import CorpusPublishWorkspace from "./corpus-builder/CorpusPublishWorkspace.vue";
import CorpusReviewRecordPane from "./corpus-builder/CorpusReviewRecordPane.vue";
import CorpusReviewAdvancedMetadata from "./corpus-builder/CorpusReviewAdvancedMetadata.vue";
import CorpusReviewInspector from "./corpus-builder/CorpusReviewInspector.vue";
import CorpusReviewHeader from "./corpus-builder/CorpusReviewHeader.vue";
import CorpusReviewRunStatus from "./corpus-builder/CorpusReviewRunStatus.vue";
import type { CorpusSetupSectionId } from "../features/corpus-builder/domain/setupState";
import { useCorpusSourceView } from "../features/corpus-builder/composables/useCorpusSourceView";
import { useCorpusSetupState } from "../features/corpus-builder/composables/useCorpusSetupState";
import { useCorpusWorkspaceNavigation } from "../features/corpus-builder/composables/useCorpusWorkspaceNavigation";
import CorpusReviewRecordQueue from "./corpus-builder/CorpusReviewRecordQueue.vue";
import CorpusReviewEvidencePanel from "./corpus-builder/CorpusReviewEvidencePanel.vue";
import CorpusRecordSizeAdvice from "./CorpusRecordSizeAdvice.vue";
import CorpusUnitPolicy from "./CorpusUnitPolicy.vue";
import CorpusTopologyPolicyControl from "./corpus-builder/CorpusTopologyPolicy.vue";
import CorpusReviewSourcePanel from "./corpus-builder/CorpusReviewSourcePanel.vue";
import CorpusEnrichmentConfiguration from "./corpus-builder/CorpusEnrichmentConfiguration.vue";
import CorpusSemanticWorkspace from "./corpus-builder/CorpusSemanticWorkspace.vue";
import CorpusRecordSemanticMap from "./corpus-builder/CorpusRecordSemanticMap.vue";
import CorpusMetadataConfiguration from "./corpus-builder/CorpusMetadataConfiguration.vue";
import CorpusMissingDocumentFields from "./corpus-builder/CorpusMissingDocumentFields.vue";
import { missingRequiredDocumentFields, suppliedDocumentMetadata } from "../domain/documentFields";
import CorpusAdvancedConfiguration from "./corpus-builder/CorpusAdvancedConfiguration.vue";
import { type CorpusActionMenuItem } from "./CorpusActionMenu.vue";
import CorpusRecordDecisionDock from "./corpus-builder/CorpusRecordDecisionDock.vue";
import { RecordMutationQueue } from "../domain/recordMutationQueue";
import { hideSourceWarnings, sourceWarningsHidden } from "../domain/sourceQuality";
import { recurringShortLines } from "../domain/textCleanup";
import { allEvidenceBlockIds } from "../domain/metadataEvidence";
import * as runtime from "../runtime/runtime.js";

const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const builds = ref<CorpusBuild[]>([]);
const buildsTotal = ref(0);
const corpusProfiles = ref<Array<Record<string, unknown>>>([]);
const recordSourceWarningOpen = ref(false);
const sourceProblemDialogBuildId = ref("");
const selectedBuildId = ref("");
const currentBuild = ref<CorpusBuild | null>(null);
const {
  providerProfiles,
  serverProviderIds,
  selectedProviderId,
  selectedReviewProviderId,
  llmActionProviderId,
  llmActionModel,
  manualProvider,
  manualModel,
  manualBaseUrl,
  manualApiKey,
  useProfileDefaults,
  generationOverrides,
  maxConcurrentRequests,
  stageLimits,
  stageTimeouts,
  recordSizing,
  enrichmentMode,
  semanticIndexing,
  documentIntelligenceProfile,
  documentNlpProvider,
  documentNlpIncludeEvents,
  autoCleanText,
  llmTouchupDuringEnrichment,
  noiseUnusableThreshold,
  llmAssessTextNoise,
  selectedProfileModel,
  effectiveGeneration,
  contextSafe,
  selectedProviderLabel,
  providerPayload,
  directProfilePayload,
  directProfilePayloadWithModel,
  refreshProviders,
  applyBuildRequest,
} = useCorpusProviderConfiguration(currentBuild);
const recordOffset = ref(0);
const pageSize = 50;
const selectedRecordId = ref("");
const selectedRecord = ref<CorpusRecord | null>(null);
const recordPopout = ref<{ recordId: string; text: string } | null>(null);
const justProcessedRecordId = ref("");
const sourceBlocks = ref<SourceBlock[]>([]);
const selectedEvidenceField = ref("");
const selectedPdfPage = ref(1);
const reviewQueue = ref<ReviewQueue>("all");
// Set when a Finish blocker sends the reviewer into the "all" queue, which
// otherwise looks identical to the Finish workspace.
const reviewRequested = ref(false);
const {
  reviewQueueCollapsed,
  reviewInspectorTab,
  reviewWorkspaceMode,
  recordQuery,
  selectedReviewIds,
  selectedReviewCount,
  focusView,
  focusHistory,
  focusHistoryOffsets,
  focusHistoryIndex,
  recordListEl,
  reviewPaneEl,
  reviewInspectorEl,
  captureReviewViewport,
  restoreReviewViewport,
  focusFirstMetadataBlocker,
  setReviewWorkspaceMode,
  reviewInspectorKeydown,
} = useCorpusReviewWorkspace();
function setRecordListElement(element: HTMLElement | null) {
  recordListEl.value = element;
}
// The queue list holds lightweight rows; full Records are read one at a time when opened.
const reviewRecords = useCorpusReviewRecords({
  selectedBuildId,
  currentBuild,
  recordOffset,
  pageSize,
  reviewQueue,
  recordQuery,
  selectedRecordId,
  selectedRecord,
  hasActiveDraft: () =>
    editingText.value || metadataEditorDirty.value || advancedMetadataDirty.value,
  activateRecord,
  onSelectionCleared: () => {
    sourceBlocks.value = [];
  },
  onPageLoaded: offerFirstSourceProblem,
  onFacets: (values) => {
    metadataObservedValues.value = values;
  },
  onError: (message) => setMessage(message, "error"),
});
const {
  queueRows,
  recordTotal,
  recordsLoading,
  reviewHydrated,
  hydratedTopologyCount,
  loadingRecordId,
  recordError,
  refreshRecords,
  applyRecord: applyRecordToQueue,
} = reviewRecords;
async function selectRecord(target: ReviewTarget) {
  return reviewRecords.selectRecord(target);
}
// Optimistic edits replace selectedRecord; keep the cached copy in step so returning to this Record
// shows what the reviewer last saw rather than the version read before the edit.
watch(selectedRecord, (record) => {
  if (record) reviewRecords.remember(record);
});
// Hands-free mode: nobody reviews, a stated policy decides (see the server's autonomous.py). Off unless turned on.
const handsFree = ref<AutonomousPolicy>({
  enabled: false,
  passes: 1,
  min_confidence: 0.8,
  unresolved: "best_guess",
  accept_records: true,
  publish: false,
});
const handsFreeOpen = ref(false);
const topologyPolicy = ref<CorpusTopologyPolicy>({
  mode: "semantic",
  source_units_per_record: 1,
  records_per_page: null,
});
function applyCorpusBuildRequest(request: Record<string, unknown>) {
  applyBuildRequest(request);
  const saved =
    request.topology_policy && typeof request.topology_policy === "object"
      ? (request.topology_policy as Partial<CorpusTopologyPolicy>)
      : {};
  topologyPolicy.value = {
    mode: saved.mode === "source_units" ? "source_units" : "semantic",
    source_units_per_record: Math.max(1, Math.min(100, Number(saved.source_units_per_record || 1))),
    records_per_page:
      saved.records_per_page == null
        ? null
        : Math.max(1, Math.min(100, Number(saved.records_per_page || 1))),
  };
}
// The metadata schema a new build follows: which fields records have and what the model looks for. A build keeps a copy.
const schemaId = ref("default");
const schemaChoices = ref<SchemaSummary[]>([]);
const schemaEditorOpen = ref(false);
function openSchemasPage() {
  schemaEditorOpen.value = false;
  void router.push({ name: "schemas" });
}
const selectedSchema = ref<MetadataSchema | null>(null);
const {
  guidance: runGuidance,
  fields: runGuidanceFields,
  active: activeRunGuidance,
  payload: runGuidancePayload,
} = useCorpusRunGuidance(selectedSchema, currentBuild, (key, fallback) => i18n.t(key, fallback));
async function loadSelectedSchema(id: string) {
  try {
    const loaded = await metadataSchemasApi.get(id);
    if (schemaId.value === id) selectedSchema.value = loaded;
  } catch {
    if (schemaId.value === id) selectedSchema.value = null;
  }
}
async function loadSchemaChoices() {
  try {
    // A response without a list must not leave the choices undefined: every lookup below would then throw.
    const items = (await metadataSchemasApi.list())?.items;
    schemaChoices.value = Array.isArray(items) ? items : [];
    if (!schemaChoices.value.some((item) => item.id === schemaId.value)) schemaId.value = "default";
  } catch {
    /* the built-in schema still works without the list */
  } finally {
    await loadSelectedSchema(schemaId.value);
  }
}
watch(schemaId, (id) => {
  void loadSelectedSchema(id);
});
const chosenSchema = computed(() => schemaChoices.value.find((item) => item.id === schemaId.value));
async function runHandsFree() {
  if (!currentBuild.value) return;
  busy.value = "hands-free";
  try {
    const config =
      directProfilePayloadWithModel(
        llmActionProviderId.value ||
          selectedProviderId.value ||
          providerProfiles.value[0]?.id ||
          "",
        llmActionModel.value,
      ) || providerPayload.value;
    currentBuild.value = await corpusBuilderApi.runAutonomous(currentBuild.value.build_id, {
      ...config,
      autonomous: { ...handsFree.value, enabled: true },
    });
    handsFreeOpen.value = false;
    startPolling();
    setMessage(i18n.t("pdf_corpus.hands_free_started"));
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
function openHandsFreeException(recordId: string) {
  reviewQueue.value = "all";
  recordQuery.value = recordId;
}
const hydratedMetadataCount = ref(0);
const busy = ref("");
const {
  assets,
  selectedAssetId,
  selectedAsset,
  sourceIllegibility,
  sourceUrl,
  gutenbergQuery,
  gutenbergHits,
  wikisourceHits,
  wikisourceLanguage,
  librarySearched,
  libraryError,
  libraryImporting,
  libraryImported,
  importLibraryUrl,
  gutenbergStatus,
  lastIngestedAsset,
  languagePrompt,
  saveSourceLanguage,
  applyPageEstimate,
  refreshAssets,
  upload,
  applyUnitPolicy,
  deleteAsset,
  loadSourceUrl,
  searchGutenberg,
  searchWikisource,
  refreshGutenbergStatus,
  refreshGutenbergCatalogue,
  updateGutenbergArchive,
  importGutenberg,
  savePageLabels,
  saveDocumentLayout,
} = useCorpusSourceConfiguration(
  busy,
  setMessage,
  () => selectedProviderId.value,
  (profileId) => directProfilePayload(profileId),
);
const syntheticRecordPagesAvailable = computed(() => {
  const asset = selectedAsset.value;
  if (!asset) return false;
  const mediaKind = String(asset.media_kind || "").toLowerCase();
  if (["pdf", "image", "audio"].includes(mediaKind)) return false;
  return String(asset.page_number_detection?.status || "") !== "detected";
});
const topologySummary = computed(() => {
  if (topologyPolicy.value.mode === "semantic") {
    return i18n.t("pdf_corpus.topology.semantic_summary", "Semantic boundaries determine Records");
  }
  const units = topologyPolicy.value.source_units_per_record;
  const records =
    units === 1 ? "1 SourceUnit → 1 Record" : `${units.toLocaleString()} SourceUnits → 1 Record`;
  const perPage = topologyPolicy.value.records_per_page;
  return perPage && syntheticRecordPagesAvailable.value
    ? `${records} → ${perPage.toLocaleString()} ${
        perPage === 1 ? "Record" : "Records"
      } per synthetic Page`
    : records;
});

const error = ref("");
const notice = ref("");
const statusRegion = ref<HTMLElement | null>(null);
const decisionDock = ref<InstanceType<typeof CorpusRecordDecisionDock> | null>(null);
const configurationSection = ref<CorpusSetupSectionId | "">("source");
const recordSaveQueue = new RecordMutationQueue();
const documentMetadataOpen = ref(false);
const missingMetadataPromptOpen = ref(false);
/** Skipping review is offered once processing is done and until a publication exists. */
const canPublishUnreviewed = computed(() =>
  Boolean(
    currentBuild.value &&
      !currentBuild.value.publication &&
      Number(currentBuild.value.record_count || 0) > 0 &&
      ["ready", "awaiting_review"].includes(String(currentBuild.value.status || "")),
  ),
);
async function publishUnreviewed() {
  await publishAndShow({ acceptUnreviewed: true });
}
/** A successful publication lands on the Publish workspace, which shows the published snapshot. */
async function publishAndShow(options: { acceptUnreviewed?: boolean } = {}) {
  const result = await publish({ download: false, ...options });
  if (result) await switchWorkspace("publish");
  return result;
}
const textCleanupOpen = ref(false);
const sourceTranscriptionOpen = ref(false);
const {
  textDraft,
  editingText,
  resolveSourceOnTextSave,
  llmTouchupOpen,
  llmTouchupResult,
  llmTouchupError,
  beginTextEdit,
  cancelTextEdit,
  saveReviewedText,
  markTextReviewed,
  saveTextFromFocus,
  saveSourceTranscription,
  openLlmTouchup,
  runLlmTouchup,
  dismissLlmTouchup,
  applyLlmTouchup,
} = useCorpusTextReview({
  currentBuild,
  selectedBuildId,
  selectedRecord,
  applyRecordToQueue: applyRecordToQueue,
  busy,
  sourceTranscriptionOpen,
  llmActionProviderId,
  llmActionModel,
  selectedProviderId,
  providerProfiles,
  directProfilePayloadWithModel,
  captureReviewViewport,
  restoreReviewViewport,
  queueRecordRequest,
  applyAuthoritativeRecord,
  textDraftKey,
  setMessage,
  t: (key, fallback) => i18n.t(key, fallback),
});
const bulkActionFeedback = ref("");
const {
  reviewQueueCounts,
  pendingCount,
  issueCount,
  readyCount,
  topologyIssueCount,
  buildRunning,
  reviewLocked,
  structuralReviewLocked,
  canResume,
  segmentationNeedsReview,
  retryingSegmentation,
  canRetryMetadata,
  metadataIssueCount,
  awaitingManifestReview,
  hasRecordTopology,
  showReviewWorkspace: lifecycleShowReviewWorkspace,
} = useCorpusBuildLifecycle(currentBuild, recordTotal, reviewQueue, reviewRequested);

const activeEnrichingRecordIds = computed(
  () =>
    new Set(
      (currentBuild.value?.metadata_active_tasks || [])
        .map((task) => String(task?.record_id || ""))
        .filter(Boolean),
    ),
);
const activeEnrichingCount = computed(() => activeEnrichingRecordIds.value.size);
const queuedPreparingCount = computed(() =>
  Math.max(0, Number(reviewQueueCounts.value.preparing ?? 0) - activeEnrichingCount.value),
);

const { workspaceMode, switchWorkspace } = useCorpusWorkspaceNavigation({
  currentBuild,
  hasRecordTopology,
  reviewReady: lifecycleShowReviewWorkspace,
});
const showReviewWorkspace = computed(
  () =>
    workspaceMode.value === "review" && hasRecordTopology.value && !awaitingManifestReview.value,
);
const documentMetadata = ref<Record<string, unknown>>({});
watch(selectedAssetId, () => {
  documentMetadata.value = {};
  topologyPolicy.value = {
    mode: "semantic",
    source_units_per_record: 1,
    records_per_page: null,
  };
});
const effectiveSetupDocumentMetadata = computed<Record<string, unknown>>(() => ({
  ...((selectedAsset.value?.initial_metadata || {}) as Record<string, unknown>),
  ...documentMetadata.value,
}));
// Required fields react to reviewer edits as well as ingest detection. Clearing a detected
// required field therefore makes Setup incomplete instead of failing much later at Publish.
const missingDocumentFields = computed(() =>
  selectedAsset.value?.deterministic_checked_at
    ? missingRequiredDocumentFields(selectedSchema.value, effectiveSetupDocumentMetadata.value)
    : [],
);
const setupManifest = computed<Record<string, unknown>>(() => {
  const initial = {
    ...((selectedAsset.value?.initial_metadata || {}) as Record<string, unknown>),
  };
  const provenance =
    initial.field_provenance && typeof initial.field_provenance === "object"
      ? (initial.field_provenance as Record<string, Record<string, unknown>>)
      : {};
  const applied = Object.fromEntries(
    Object.entries(provenance)
      .filter(([name]) => initial[name] !== undefined)
      .map(([name, info]) => [name, { ...info, value: initial[name] }]),
  );
  return {
    ...effectiveSetupDocumentMetadata.value,
    ...(Object.keys(applied).length ? { deterministic_ingest: { applied } } : {}),
  };
});
function saveSetupManifest(changes: Record<string, unknown>) {
  documentMetadata.value = { ...documentMetadata.value, ...changes };
}
const setupDocumentMetadataOverrideCount = computed(
  () => Object.keys(documentMetadata.value).length,
);
const documentMetadataPayload = () =>
  Object.fromEntries(
    Object.entries(documentMetadata.value).map(([name, value]) => [
      name,
      typeof value === "string" ? value.trim() || null : value,
    ]),
  );
const missingDocumentMetadata = computed<Record<string, string>>({
  get: () =>
    Object.fromEntries(
      missingDocumentFields.value.map(({ name }) => [
        name,
        String(documentMetadata.value[name] ?? "").trim(),
      ]),
    ),
  set: (values) => {
    documentMetadata.value = { ...documentMetadata.value, ...values };
  },
});
const missingMetadataComplete = computed(
  () =>
    Object.keys(
      suppliedDocumentMetadata(missingDocumentFields.value, missingDocumentMetadata.value),
    ).length === missingDocumentFields.value.length,
);

const {
  registerBuildOperation,
  syncBuildInRail,
  refreshBuilds,
  refreshBuild,
  startPolling,
  stopPolling,
  startBuild: startBuildOperation,
  resumeBuild,
  retryIncompleteMetadata,
  confirmManifest,
  cancelBuild,
  pauseBuild,
  deleteBuild,
  settleMetadata,
} = useCorpusBuildLifecycleController({
  builds,
  buildsTotal,
  selectedBuildId,
  currentBuild,
  selectedAssetId,
  assets,
  busy,
  schemaId,
  providerPayload,
  handsFree,
  hydratedTopologyCount,
  hydratedMetadataCount,
  selectedRecordId,
  canRetryMetadata,
  metadataIssueCount,
  requestedBuildId: () => String(route.query.build || ""),
  runGuidancePayload,
  documentMetadataPayload,
  topologyPolicyPayload: () => ({ ...topologyPolicy.value }),
  applyBuildRequest: applyCorpusBuildRequest,
  setMessage,
  resetReviewForBuildStart: () => {
    hydratedMetadataCount.value = 0;
    reviewRecords.clear();
    selectedRecord.value = null;
    sourceBlocks.value = [];
  },
  refreshRecords,
  refreshRows: reviewRecords.refreshRows,
  refreshRecord: reviewRecords.refreshRecord,
  t: (key, fallback) => i18n.t(key, fallback),
  tf: (key, values) => i18n.tf(key, values),
});
async function startBuild(fromMetadataPrompt = false) {
  if (!fromMetadataPrompt && missingDocumentFields.value.length && !missingMetadataComplete.value) {
    missingMetadataPromptOpen.value = true;
    return;
  }
  await startBuildOperation();
  if (currentBuild.value) await switchWorkspace("build");
}
async function continueBuildWithDocumentMetadata() {
  missingMetadataPromptOpen.value = false;
  await startBuild(true);
}

const { jsonlPreviewOpen, jsonlPreview, openJsonlPreview, publish } = useCorpusPublication({
  currentBuild,
  selectedRecord,
  busy,
  setMessage,
  refreshBuild,
  refreshBuilds,
  t: (key, fallback) => i18n.t(key, fallback),
  tf: (key, values) => i18n.tf(key, values),
});
const {
  metadataSavingField,
  metadataSavedField,
  metadataDraft,
  bulkMetadataOpen,
  metadataEnrichmentOpen,
  metadataEditorDirty,
  editorialMemoryOpen,
  editorialMemory,
  metadataRerunFamily,
  metadataObservedValues,
  metadataKnownValues,
  saveMetadata,
  toggleEvidenceBlock,
  setEvidenceBlocks,
  setExternalEvidenceBlocks,
  requeueCurrentRecord,
  resolveMetadataField,
  resolveMetadataSuggestions,
  resolveMetadataNoValue,
  clearMetadataSuggestionCache,
  runMetadataEnrichment,
  openEditorialMemory,
  resetEditorialMemory,
  handleMetadataDirty,
  showMetadataSource,
  rerunMetadata,
  applyBulkMetadata,
} = useCorpusMetadataReview({
  currentBuild,
  selectedRecord,
  selectedRecordId,
  applyRecordToQueue: applyRecordToQueue,
  busy,
  selectedEvidenceField,
  reviewInspectorTab,
  selectedPdfPage,
  sourceBlocks,
  selectedReviewIds,
  reviewQueue,
  recordQuery,
  llmActionProviderId,
  llmActionModel,
  selectedProviderId,
  providerProfiles,
  directProfilePayloadWithModel,
  captureReviewViewport,
  restoreReviewViewport,
  queueRecordRequest,
  applyAuthoritativeRecord,
  syncBuildInRail,
  registerBuildOperation,
  startPolling,
  refreshBuild,
  refreshRecords,
  recordMetadata,
  metadataDraftKey,
  setMessage,
  t: (key, fallback) => i18n.t(key, fallback),
  tf: (key, fallbackOrValues, values) => i18n.tf(key, fallbackOrValues, values),
});

function normalizedEvidenceWords(value: string) {
  return new Set(
    value
      .toLocaleLowerCase()
      .split(/[^\p{L}\p{N}]+/u)
      .map((item) => item.trim())
      .filter((item) => item.length > 2),
  );
}

function evidenceBlockForSelection(selectedText: string) {
  const selected = selectedText.replace(/\s+/g, " ").trim().toLocaleLowerCase();
  if (!selectedRecord.value || !selected) return null;
  const allowedIds = new Set((selectedRecord.value.source_block_ids || []).map(String));
  const candidates = sourceBlocks.value.filter((block) => allowedIds.has(String(block.block_id)));
  const exact = candidates.find((item) =>
    String(item.text || "")
      .replace(/\s+/g, " ")
      .toLocaleLowerCase()
      .includes(selected),
  );
  if (exact) return exact;
  const wanted = normalizedEvidenceWords(selected);
  let best: (typeof candidates)[number] | null = null;
  let score = 0;
  for (const item of candidates) {
    const words = normalizedEvidenceWords(String(item.text || ""));
    const overlap = [...wanted].filter((word) => words.has(word)).length;
    const next = wanted.size ? overlap / wanted.size : 0;
    if (next > score) {
      score = next;
      best = item;
    }
  }
  return score >= 0.45 ? best : null;
}

/**
 * "Save and use selected text as evidence": one optimistic save of the value together with the
 * nearest source block as its evidence. The reviewer stays on the metadata tab and the field
 * list moves on to the next value awaiting review.
 */
async function resolveMetadataWithSelectionEvidence(
  field: string,
  value: unknown,
  selectedText: string,
) {
  const block = evidenceBlockForSelection(selectedText);
  if (!block?.block_id) {
    // Nothing in this record matches the selection: keep the value, say why, and bind no evidence.
    setMessage(i18n.t("pdf_corpus.selection_no_matching_block"), "error");
    await resolveMetadataField(field, value);
    return;
  }
  await resolveMetadataField(field, value, String(block.block_id));
}

/** What the reviewer came from Publication readiness to fix, so they can stay in one task. */
interface FixContext {
  recordId: string;
  field: string;
  code: string;
  label: string;
  reason: string;
  queue: ReviewQueue | "";
  initialTotal: number;
}
const fixContext = ref<FixContext | null>(null);
const fixIssues = computed(() =>
  (currentBuild.value?.validation?.validation_issues || []).filter((item) => item?.record_id),
);
function publicationBlockerCount(code: string) {
  const blocker = (currentBuild.value?.publication_readiness?.blockers || []).find(
    (item) => String(item?.code || "") === code,
  );
  if (blocker) return Math.max(0, Number(blocker.count || 0));
  if (code === "review_pending") return Math.max(0, Number(pendingCount.value || 0));
  if (code === "record_attention") return Math.max(0, Number(issueCount.value || 0));
  if (code === "boundary_attention") return Math.max(0, Number(topologyIssueCount.value || 0));
  if (code === "required_metadata") return Math.max(0, Number(metadataIssueCount.value || 0));
  if (code === "metadata_validation") return fixIssues.value.length;
  if (code === "source_quality")
    return Math.max(
      0,
      Number(reviewQueueCounts.value.source ?? currentBuild.value?.source_problem_count ?? 0),
    );
  return 0;
}
function remediationLabel(code: string) {
  return i18n.t(
    `pdf_corpus.readiness_blocker.${code || "unknown"}`,
    String(code || "unknown").replace(/_/g, " "),
  );
}
const fixRemaining = computed(() =>
  fixContext.value ? publicationBlockerCount(fixContext.value.code) : 0,
);
/** Progress is anchored to the blocker count seen when the remediation session started. */
const fixProgress = computed(() => {
  const current = fixContext.value;
  if (!current || current.initialTotal <= 0) return null;
  const total = current.initialTotal;
  const remaining = Math.min(total, Math.max(0, fixRemaining.value));
  return {
    position: Math.min(total, Math.max(1, total - remaining + 1)),
    total,
    remaining,
  };
});
function beginQueueRemediation(code: string) {
  const total = publicationBlockerCount(code);
  if (total <= 0) {
    fixContext.value = null;
    return;
  }
  fixContext.value = {
    code,
    label: remediationLabel(code),
    recordId: selectedRecordId.value,
    field: "",
    reason: "",
    queue: reviewQueue.value,
    initialTotal: total,
  };
}
/** Land on the record, on the tab that holds the problem, with the field's editor open. */
async function fixValidationIssue(issue: {
  code?: string;
  record_id?: string;
  field?: string;
  reason?: string;
}) {
  const recordId = String(issue.record_id || "");
  if (!recordId) return;
  const field = String(issue.field || "");
  const initialTotal =
    fixContext.value?.code === "metadata_validation"
      ? fixContext.value.initialTotal
      : Math.max(1, publicationBlockerCount("metadata_validation"), fixIssues.value.length);
  fixContext.value = {
    recordId,
    field,
    code: "metadata_validation",
    label: remediationLabel("metadata_validation"),
    reason: String(issue.reason || ""),
    queue: "all",
    initialTotal,
  };
  await openValidationIssueQueue(recordId);
  // The reviewer may have left the split "record" view in a full-screen Source or
  // Metadata workspace mode on whatever record they last touched. The metadata and
  // evidence panels below only render in "record" mode, so without this the fix
  // navigation silently lands on the record with no visible way to see the problem.
  setReviewWorkspaceMode("record");
  await nextTick();
  if (!field) return;
  if (issue.code === "metadata_evidence") {
    reviewInspectorTab.value = "evidence";
    selectedEvidenceField.value = field;
    return;
  }
  reviewInspectorTab.value = "metadata";
  await nextTick();
  const target = document.querySelector<HTMLElement>(`[data-field="${CSS.escape(field)}"]`);
  target?.scrollIntoView({ block: "center" });
  target?.querySelector<HTMLElement>("select, textarea, input")?.focus({ preventScroll: true });
}
/** Go on to the next finding in this remediation session. */
async function fixNextIssue() {
  const current = fixContext.value;
  if (!current) return;
  if (current.code === "metadata_validation") {
    const index = fixIssues.value.findIndex(
      (item) => item.record_id === current.recordId && item.field === current.field,
    );
    const next = fixIssues.value[index + 1] || fixIssues.value[0];
    if (!next || fixIssues.value.length <= 1) return;
    await fixValidationIssue(next);
    return;
  }
  if (fixRemaining.value <= 0) return returnToReadiness();
  await focusQueueMove(1);
}
/** Leave a fix context and return to Publication readiness, which is the Publish workspace. */
function returnToReadiness() {
  fixContext.value = null;
  reviewRequested.value = false;
  reviewQueue.value = "all";
  recordQuery.value = "";
  void switchWorkspace("publish");
}
let remediationAdvancing = false;
watch(fixRemaining, async (remaining, previous) => {
  const current = fixContext.value;
  if (!current || workspaceMode.value !== "review" || previous <= remaining) return;
  // Record decisions and metadata review already own their queue-aware advancement.
  // When the blocker itself disappears, return to the authoritative Publish readiness state.
  if (remaining === 0) {
    returnToReadiness();
    return;
  }
  if (remediationAdvancing || !["source_quality", "source_validation"].includes(current.code)) {
    return;
  }
  remediationAdvancing = true;
  await nextTick();
  await advanceFrom(current.recordId);
  remediationAdvancing = false;
});
watch(
  fixIssues,
  async (issues) => {
    const current = fixContext.value;
    if (
      !current ||
      current.code !== "metadata_validation" ||
      workspaceMode.value !== "review" ||
      remediationAdvancing
    ) {
      return;
    }
    const currentStillExists = issues.some(
      (item) => item.record_id === current.recordId && item.field === current.field,
    );
    if (currentStillExists) return;
    if (!issues.length || publicationBlockerCount("metadata_validation") === 0) {
      returnToReadiness();
      return;
    }
    remediationAdvancing = true;
    await fixValidationIssue(issues[0]);
    remediationAdvancing = false;
  },
  { deep: true },
);
watch(selectedRecordId, (recordId) => {
  const current = fixContext.value;
  if (!current || current.code === "metadata_validation" || !recordId) return;
  fixContext.value = { ...current, recordId };
});
watch(reviewQueue, (queue) => {
  const current = fixContext.value;
  if (current?.queue && current.queue !== queue) fixContext.value = null;
});
watch(workspaceMode, (mode) => {
  if (mode !== "review" && fixContext.value) fixContext.value = null;
});
async function adjudicateBoundaryWithRemediation(
  direction: "previous" | "next",
  profileId?: string,
  model?: string,
) {
  const current = fixContext.value;
  const before = current?.code === "boundary_attention" ? fixRemaining.value : 0;
  const recordId = selectedRecordId.value;
  await adjudicateBoundary(direction, profileId, model);
  if (
    !current ||
    current.code !== "boundary_attention" ||
    workspaceMode.value !== "review" ||
    fixContext.value?.code !== "boundary_attention"
  ) {
    return;
  }
  const remaining = fixRemaining.value;
  if (remaining >= before) return;
  if (remaining === 0) {
    returnToReadiness();
    return;
  }
  await advanceFrom(recordId);
}

/** The reviewer answers from their own knowledge: the decision records them, not a source span, as the source. */
async function resolveMetadataWithHumanSource(field: string, value: unknown, note: string) {
  await resolveMetadataField(field, value, "", { source: "reviewer_knowledge", note });
}

/** The value being cited from outside this record, while the browser dialog is open. */
// From a field editor the chosen spans are saved with the value; from the Evidence tab (`evidenceOnly`) they replace
// the field's other-record spans and leave its value alone.
const evidenceBrowser = ref<{ field: string; value?: unknown; evidenceOnly?: boolean } | null>(
  null,
);
function openEvidenceBrowser(field: string, value: unknown) {
  evidenceBrowser.value = { field, value };
}
function openExternalEvidenceBrowser(field: string) {
  if (field) evidenceBrowser.value = { field, evidenceOnly: true };
}
async function confirmExternalEvidence(blockIds: string[]) {
  const target = evidenceBrowser.value;
  evidenceBrowser.value = null;
  if (!target) return;
  if (target.evidenceOnly) await setExternalEvidenceBlocks(target.field, blockIds);
  else await resolveMetadataField(target.field, target.value, "", { externalBlockIds: blockIds });
}

const metadataFamilyOptions = computed(
  () =>
    currentBuild.value?.schema?.groups?.map((group) => ({
      key: group.key,
      label: group.label,
    })) || [
      {
        key: "discourse",
        label: i18n.t("pdf_corpus.metadata_family.discourse"),
      },
      {
        key: "quotation",
        label: i18n.t("pdf_corpus.metadata_family.quotation"),
      },
      {
        key: "indexing",
        label: i18n.t("pdf_corpus.metadata_family.indexing"),
      },
    ],
);
const DRAFT_KEY = "derridai.pdf-corpus-builder.draft.v2";
function restoreBuilderDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return;
    const draft = JSON.parse(raw) as Record<string, unknown>;
    if (typeof draft.selectedAssetId === "string") selectedAssetId.value = draft.selectedAssetId;
    if (
      typeof draft.manualProvider === "string" &&
      (draft.manualProvider === "ollama" || draft.manualProvider === "openai")
    )
      manualProvider.value = draft.manualProvider;
    if (typeof draft.manualModel === "string") manualModel.value = draft.manualModel;
    if (typeof draft.manualBaseUrl === "string") manualBaseUrl.value = draft.manualBaseUrl;
    if (typeof draft.useProfileDefaults === "boolean")
      useProfileDefaults.value = draft.useProfileDefaults;
    if (draft.generationOverrides && typeof draft.generationOverrides === "object")
      generationOverrides.value = { ...draft.generationOverrides };
    if (draft.stageLimits && typeof draft.stageLimits === "object")
      stageLimits.value = { ...stageLimits.value, ...draft.stageLimits };
    if (draft.stageTimeouts && typeof draft.stageTimeouts === "object")
      stageTimeouts.value = { ...stageTimeouts.value, ...draft.stageTimeouts };
    if (draft.recordSizing && typeof draft.recordSizing === "object")
      recordSizing.value = { ...recordSizing.value, ...draft.recordSizing };
    if (Number.isFinite(Number(draft.maxConcurrentRequests)))
      maxConcurrentRequests.value = Math.max(1, Math.min(64, Number(draft.maxConcurrentRequests)));
    if (draft.enrichmentMode === "fast" || draft.enrichmentMode === "deep")
      enrichmentMode.value = draft.enrichmentMode;
    if (typeof draft.semanticIndexing === "boolean")
      semanticIndexing.value = draft.semanticIndexing;
    if (
      draft.documentIntelligenceProfile === "none" ||
      draft.documentIntelligenceProfile === "general" ||
      draft.documentIntelligenceProfile === "fiction" ||
      draft.documentIntelligenceProfile === "scholarly"
    )
      documentIntelligenceProfile.value = draft.documentIntelligenceProfile;
    if (
      draft.documentNlpProvider === "auto" ||
      draft.documentNlpProvider === "spacy" ||
      draft.documentNlpProvider === "booknlp"
    )
      documentNlpProvider.value = draft.documentNlpProvider;
    if (typeof draft.documentNlpIncludeEvents === "boolean")
      documentNlpIncludeEvents.value = draft.documentNlpIncludeEvents;
    if (typeof draft.autoCleanText === "boolean") autoCleanText.value = draft.autoCleanText;
    if (typeof draft.llmTouchupDuringEnrichment === "boolean")
      llmTouchupDuringEnrichment.value = draft.llmTouchupDuringEnrichment;
    if (Number.isFinite(Number(draft.noiseUnusableThreshold)))
      noiseUnusableThreshold.value = Math.max(
        0,
        Math.min(100, Number(draft.noiseUnusableThreshold)),
      );
    if (typeof draft.llmAssessTextNoise === "boolean")
      llmAssessTextNoise.value = draft.llmAssessTextNoise;
  } catch {
    /* ignore stale browser drafts */
  }
}
function persistBuilderDraft() {
  try {
    localStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({
        selectedAssetId: selectedAssetId.value,
        manualProvider: manualProvider.value,
        manualModel: manualModel.value,
        manualBaseUrl: manualBaseUrl.value,
        useProfileDefaults: useProfileDefaults.value,
        generationOverrides: generationOverrides.value,
        stageLimits: stageLimits.value,
        stageTimeouts: stageTimeouts.value,
        recordSizing: recordSizing.value,
        maxConcurrentRequests: maxConcurrentRequests.value,
        enrichmentMode: enrichmentMode.value,
        semanticIndexing: semanticIndexing.value,
        documentIntelligenceProfile: documentIntelligenceProfile.value,
        documentNlpProvider: documentNlpProvider.value,
        documentNlpIncludeEvents: documentNlpIncludeEvents.value,
        autoCleanText: autoCleanText.value,
        llmTouchupDuringEnrichment: llmTouchupDuringEnrichment.value,
        noiseUnusableThreshold: noiseUnusableThreshold.value,
        llmAssessTextNoise: llmAssessTextNoise.value,
      }),
    );
  } catch {
    /* storage may be unavailable */
  }
}
function metadataDraftKey(buildId: string, recordId: string) {
  return `derridai.pdf-corpus.metadata-draft.${buildId}.${recordId}`;
}
function textDraftKey(buildId: string, recordId: string) {
  return `derridai.pdf-corpus.text-draft.${buildId}.${recordId}`;
}
const {
  open: ingestWarningOpen,
  maybeOpen: maybeOpenIngestWarning,
  acknowledge: acknowledgeIngestWarning,
} = useCorpusIngestWarning(selectedAsset);
watch(lastIngestedAsset, (asset) => {
  if (asset) maybeOpenIngestWarning(asset);
});

function openRecordSourceWarning(target: ReviewTarget) {
  void selectRecord(target);
  recordSourceWarningOpen.value = true;
}
function acknowledgeRecordSourceWarning(dontShowAgain = false) {
  if (dontShowAgain) hideSourceWarnings();
  recordSourceWarningOpen.value = false;
}
const evidenceBlockIds = computed(() => {
  if (!selectedRecord.value) return new Set<string>();
  if (selectedEvidenceField.value) {
    const info = selectedRecord.value.metadata_evidence?.[selectedEvidenceField.value];
    return new Set(allEvidenceBlockIds(info));
  }
  return new Set(
    Object.values(selectedRecord.value.metadata_evidence || {}).flatMap((info) =>
      allEvidenceBlockIds(info),
    ),
  );
});
const evidenceCandidateFields = computed(() => {
  const record = selectedRecord.value;
  if (!record) return [];
  return evidenceCandidateFieldNames(
    record as unknown as Record<string, unknown>,
    currentBuild.value?.schema || selectedSchema.value,
  );
});
const visibleBlocks = computed(() => {
  const record = selectedRecord.value;
  const ids = new Set(
    [
      ...(record?.source_block_ids || []),
      ...(record?.source_unit_ids || []),
      ...((record?.source_spans || [])
        .map((span) => span.source_unit_id || span.block_id)
        .filter(Boolean) as string[]),
    ].map(String),
  );
  return sourceBlocks.value.filter((block) => ids.has(block.block_id));
});
// Repeated short lines (running heads) are found across the visible page's text, read only when
// the clean-up dialog opens: queue rows never carry full text.
const cleanupPageTexts = ref<string[]>([]);
watch(textCleanupOpen, async (open) => {
  cleanupPageTexts.value = [];
  if (!open) return;
  try {
    cleanupPageTexts.value = await reviewRecords.visiblePageTexts();
  } catch {
    // The dialog still cleans with its other rules.
  }
});
const recurringCleanupLines = computed(() => recurringShortLines(cleanupPageTexts.value, 3));
const cleanupDocumentTerms = computed(() =>
  [
    currentBuild.value?.manifest?.title,
    currentBuild.value?.manifest?.short_title,
    currentBuild.value?.manifest?.original_title,
  ]
    .map((value) => String(value || "").trim())
    .filter(Boolean),
);
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- SA-13: preserve legacy setup binding until its owning workflow is extracted.
const metadataComplete = computed(
  () =>
    Number(currentBuild.value?.metadata_total || 0) === 0 ||
    Number(currentBuild.value?.metadata_completed || 0) >=
      Number(currentBuild.value?.metadata_total || 0),
);
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- SA-13: preserve legacy setup binding until its owning workflow is extracted.
const canPublish = computed(() => Boolean(currentBuild.value?.publication_readiness?.can_publish));
const selectedRecordIndex = computed(() =>
  queueRows.value.findIndex((row) => row.record_id === selectedRecordId.value),
);
const {
  boundarySliceOpen,
  canMergePrevious,
  canMergeNext,
  mergeUnavailable,
  sliceUnavailable,
  merge,
  split,
  createFromSelection,
  adjudicateBoundary,
} = useCorpusBoundaryReview({
  currentBuild,
  selectedRecord,
  selectedRecordId,
  queueRows,
  recordTotal,
  recordOffset,
  selectedRecordIndex,
  visibleBlocks,
  busy,
  structuralReviewLocked,
  editingText,
  metadataEditorDirty,
  llmActionProviderId,
  llmActionModel,
  selectedProviderId,
  directProfilePayloadWithModel,
  captureReviewViewport,
  restoreReviewViewport,
  queueRecordRequest,
  refreshBuild,
  refreshRecords,
  setMessage,
  t: (key, fallback) => i18n.t(key, fallback),
  tf: (key, values) => i18n.tf(key, values),
});
const {
  openFocusView,
  focusHistoryMove,
  focusQueueMove,
  navigateToQueueRecord,
  advanceFrom,
  openMetadataIssueQueue,
  openValidationIssueQueue,
  openTopologyIssueQueue,
  openIssueQueue,
  openRejectedQueue,
  openAllReviewQueue,
  openSourceIssueQueue,
  previousPage,
  nextPage,
} = useCorpusReviewNavigation({
  reviewRequested,
  currentBuild,
  queueRows,
  recordTotal,
  recordOffset,
  selectedRecord,
  selectedRecordId,
  selectedRecordIndex,
  reviewQueue,
  recordQuery,
  focusView,
  focusHistory,
  focusHistoryOffsets,
  focusHistoryIndex,
  recordListEl,
  pageSize,
  refreshRecords,
  selectRecord,
  setFilters: setReviewFilters,
});
const nextQueueRecordId = computed(() => {
  const index = selectedRecordIndex.value;
  return index >= 0 ? queueRows.value[index + 1]?.record_id || "" : "";
});
// Review is the point of this screen, so the first time a build's records are ready, bring the workspace to the top.
let reviewScrolledFor = "";
watch(
  () => [showReviewWorkspace.value, reviewHydrated.value, currentBuild.value?.build_id] as const,
  async ([show, hydrated, id]) => {
    if (!show || !hydrated || !id || reviewScrolledFor === id) return;
    reviewScrolledFor = id;
    await nextTick();
    reviewFrameEl.value?.scrollIntoView({ block: "start" });
  },
);
const reviewFrameEl = ref<HTMLElement | null>(null);
const { reviewGridEl, queueSplitter, inspectorSplitter, reviewHeightSplitter } =
  usePdfCorpusPaneSizing();
// Secondary record actions live in a menu. An action that cannot run says why instead of just being dimmed.
const recordActionItems = computed<CorpusActionMenuItem[]>(() => [
  {
    id: "previous",
    label: i18n.t("pdf_corpus.combine_previous"),
    reason: mergeUnavailable("previous"),
  },
  {
    id: "next",
    label: i18n.t("pdf_corpus.combine_next"),
    reason: mergeUnavailable("next"),
  },
  {
    id: "slice",
    label: i18n.t("pdf_corpus.slice_record"),
    reason: sliceUnavailable(),
  },
  { id: "preview", label: i18n.t("pdf_corpus.preview_jsonl") },
  {
    id: "requeue",
    label: i18n.t("pdf_corpus.requeue_metadata"),
    reason: busy.value !== "" ? i18n.t("pdf_corpus.reason.busy") : undefined,
  },
]);
function runRecordAction(id: string) {
  if (id === "previous") merge("previous");
  else if (id === "next") merge("next");
  else if (id === "slice") boundarySliceOpen.value = true;
  else if (id === "preview") openJsonlPreview();
  else if (id === "requeue") requeueCurrentRecord();
}
const bulkActionItems = computed<CorpusActionMenuItem[]>(() => {
  const rejectReason =
    busy.value !== ""
      ? i18n.t("pdf_corpus.reason.busy")
      : reviewLocked.value
        ? i18n.t("pdf_corpus.reason.review_locked")
        : selectedReviewCount.value === 0
          ? i18n.t("pdf_corpus.reason.select_records_first")
          : undefined;
  return [
    {
      id: "edit",
      label: i18n.t("pdf_corpus.bulk_edit_metadata"),
      reason: busy.value !== "" ? rejectReason : reviewLocked.value ? rejectReason : undefined,
    },
    {
      id: "hands-free",
      label: i18n.t("pdf_corpus.run_hands_free"),
      reason:
        busy.value !== ""
          ? i18n.t("pdf_corpus.reason.busy")
          : reviewLocked.value
            ? i18n.t("pdf_corpus.reason.review_locked")
            : undefined,
    },
    {
      id: "reject",
      label: i18n.tf("pdf_corpus.reject_selected_count", {
        count: selectedReviewCount.value,
      }),
      reason: rejectReason,
    },
  ];
});
function runBulkAction(id: string) {
  if (id === "edit") {
    if (busy.value || reviewLocked.value) return;
    bulkMetadataOpen.value = !bulkMetadataOpen.value;
  } else if (id === "hands-free") {
    handsFreeOpen.value = true;
  } else if (id === "reject") {
    bulkDisposition("rejected");
  }
}
const activeBuilds = computed(() =>
  builds.value.filter((build) => ["queued", "running"].includes(String(build.status || ""))),
);
const activeBuildCount = computed(() => activeBuilds.value.length);
const selectedProfileActiveBuildCount = computed(() =>
  selectedProviderId.value
    ? activeBuilds.value.filter(
        (build) => String(build.request?.provider_profile_id || "") === selectedProviderId.value,
      ).length
    : 0,
);
function providerResourceKey(profileId: string) {
  const profile = providerProfiles.value.find((p) => p.id === profileId);
  if (!profile) return profileId;
  const base = String(profile.base_url || "")
    .trim()
    .replace(/\/+$/, "")
    .toLowerCase();
  return `${profile.type || "unknown"}|${base}`;
}
const llmActionConcurrentLoad = computed(() => {
  if (!llmActionProviderId.value) return 0;
  const target = providerResourceKey(llmActionProviderId.value);
  return activeBuilds.value
    .filter((build) => {
      const id = String(build.request?.provider_profile_id || "");
      return id && providerResourceKey(id) === target;
    })
    .reduce(
      (sum, build) => sum + Math.max(1, Number(build.request?.max_concurrent_requests || 1)),
      0,
    );
});
const recordSizingValid = computed(
  () => invalidRecordSizingFields(recordSizing.value).length === 0,
);
const canStartConcurrentBuild = computed(() =>
  Boolean(
    recordSizingValid.value &&
      selectedAsset.value &&
      contextSafe.value &&
      (selectedProviderId.value || !activeBuildCount.value),
  ),
);
const transientNetworkError = computed(() =>
  Boolean(buildRunning.value && /networkerror|failed to fetch|network error/i.test(error.value)),
);
const displayError = computed(() =>
  transientNetworkError.value ? i18n.t("pdf_corpus.status_refresh_failed") : error.value,
);
const activeProviderProfileLabel = computed<string>(() => {
  const build = currentBuild.value;
  if (!build) return "—";
  const request = build.request;
  const profile =
    request && typeof request.provider_profile_id === "string" ? request.provider_profile_id : "";
  return profile || String(build.provider || "—");
});
const activeBuildProfileId = computed<string>(() => {
  const request = currentBuild.value?.request;
  return request && typeof request.provider_profile_id === "string"
    ? request.provider_profile_id
    : "";
});
const activeModelLabel = computed<string>(() => String(currentBuild.value?.model || "—"));
const pageNumber = computed(() => Math.floor(recordOffset.value / pageSize) + 1);
const pageCount = computed(() => Math.max(1, Math.ceil(recordTotal.value / pageSize)));
const {
  selectedSourceCapabilities,
  paginatedSource,
  imageSourceUrl,
  audioSourceUrl,
  sourcePdfUrl,
  recordPdfPages,
  selectedPdfPageIndex,
  selectedPageMeta,
  selectedPageBlocks,
  evidenceIdsArray,
} = useCorpusSourceView({
  selectedAsset,
  selectedAssetId,
  selectedRecord,
  selectedPdfPage,
  visibleBlocks,
  evidenceBlockIds,
});
const activeCorpusProfile = computed(
  () =>
    corpusProfiles.value.find(
      (profile) => String(profile.id || "") === String(currentBuild.value?.profile_id || ""),
    ) ||
    corpusProfiles.value.find((profile) => String(profile.id || "") === "derrida-scholarly-v12") ||
    null,
);
const regionTypes = computed(() =>
  Array.isArray(activeCorpusProfile.value?.region_types)
    ? (activeCorpusProfile.value?.region_types as unknown[]).map(String)
    : [],
);
const discourseRoles = computed(() =>
  Array.isArray(activeCorpusProfile.value?.discourse_roles)
    ? (activeCorpusProfile.value?.discourse_roles as unknown[]).map(String)
    : [],
);
function metadataBlockingFields(record: CorpusRecord | null): string[] {
  if (!record) return [];
  const allowed = new Set(
    reviewableMetadataFieldNames(
      record as unknown as Record<string, unknown>,
      currentBuild.value?.schema || selectedSchema.value,
    ),
  );
  return Array.from(
    new Set([
      ...(record.metadata_incomplete_fields || []),
      ...(record.metadata_review_fields || []),
    ]),
  ).filter((field) => allowed.has(field));
}
const selectedMetadataBlocked = computed(
  () => metadataBlockingFields(selectedRecord.value).length > 0,
);
const {
  setDisposition,
  attemptAccept,
  toggleAccept,
  rejectRecord,
  skipRecord,
  acceptCleanRecords,
  bulkDisposition,
  restoreAllRejected,
  undoReview,
  redoReview,
} = useCorpusReviewDecisions({
  currentBuild,
  selectedRecord,
  selectedRecordId,
  queueRows,
  recordTotal,
  reviewQueue,
  recordQuery,
  recordOffset,
  getSelectionVersion: reviewRecords.getSelectionVersion,
  selectedReviewIds,
  justProcessedRecordId,
  bulkActionFeedback,
  busy,
  focusView,
  reviewInspectorTab,
  reviewLocked,
  selectedMetadataBlocked,
  readyCount,
  issueCount,
  captureReviewViewport,
  restoreReviewViewport,
  queueRecordRequest,
  applyAuthoritativeRecord,
  syncBuildInRail,
  selectRecord,
  advanceFrom,
  refreshBuild,
  refreshRecords,
  focusFirstMetadataBlocker,
  setMessage,
  t: (key, fallback) => i18n.t(key, fallback),
  tf: (key, values) => i18n.tf(key, values),
});
const selectedMetadataBlockingFields = computed(() => metadataBlockingFields(selectedRecord.value));
const selectedMetadataBlockingLabel = computed(() =>
  selectedMetadataBlockingFields.value
    .map((field) => i18n.t(`record.${field}`, field.replace(/_/g, " ")))
    .join(", "),
);
const selectedRecordActivitySummary = computed(() => {
  const record = selectedRecord.value;
  if (!record) return "";
  const views = Number(record.activity?.human_view_count || record.human_view_count || 0);
  const human = Number(record.activity?.human_review_count || 0);
  const llm = Number(record.activity?.llm_review_count || 0);
  const passes = Number(record.activity?.enrichment_pass_count || 0);
  return views + human + llm + passes > 0
    ? ` · ${i18n.tf("pdf_corpus.record_activity_summary", { views, human, llm, passes })}`
    : "";
});
const selectedStructureSummary = computed(() => {
  const plan = selectedAsset.value?.document_layout;
  if (!plan) return i18n.t("pdf_corpus.readiness.structure_unset");
  const parts: string[] = [];
  parts.push(
    plan.page_layout === "two_up"
      ? i18n.t("pdf_corpus.two_up_layout")
      : i18n.t("pdf_corpus.single_page_layout"),
  );
  if (plan.main_text_pdf_start) {
    const printed = plan.main_text_printed_start
      ? i18n.tf("pdf_corpus.readiness.printed_anchor", {
          page: plan.main_text_printed_start,
        })
      : "";
    parts.push(
      i18n.tf("pdf_corpus.readiness.main_start", {
        page: plan.main_text_pdf_start,
        printed,
      }),
    );
  } else parts.push(i18n.t("pdf_corpus.readiness.main_start_unset"));
  if (plan.bibliography_pdf_start)
    parts.push(
      i18n.tf("pdf_corpus.readiness.bibliography_start", {
        page: plan.bibliography_pdf_start,
      }),
    );
  return parts.join(" · ");
});
const setupText = {
  t: (key: string, fallback?: string) => i18n.t(key, fallback),
  tf: (key: string, values: Record<string, string | number>) => i18n.tf(key, values),
};
const {
  setupIssues,
  setupSections,
  primaryStatus,
  workflowSteps,
  toggleSetupSection,
  openSetupSection,
} = useCorpusSetupState({
  text: setupText,
  currentBuild,
  selectedAsset,
  workspaceMode,
  hasRecordTopology,
  canStart: canStartConcurrentBuild,
  expandedSection: configurationSection,
  setupFacts: () => ({
    structureNeedsReview: Boolean(
      paginatedSource.value &&
        selectedAsset.value?.pages?.length &&
        !selectedAsset.value.document_layout?.main_text_pdf_start,
    ),
    structureSummary: selectedStructureSummary.value,
    recordSizingValid: recordSizingValid.value,
    topologySummary: topologySummary.value,
    targetChars: recordSizing.value.preferred_record_chars,
    toleranceChars: recordSizing.value.record_length_tolerance,
    schemaName: chosenSchema.value?.name || "",
    schemaVersion: chosenSchema.value?.schema_version || "",
    guidanceFieldCount: Object.keys(runGuidancePayload()).length,
    missingDocumentFieldCount: missingDocumentFields.value.length,
    providerLabel: selectedProviderLabel.value,
    modelLabel: selectedProfileModel.value || manualModel.value,
    enrichmentMode: enrichmentMode.value,
    documentIntelligenceProfile: documentIntelligenceProfile.value,
    profileActiveBuildCount: selectedProviderId.value ? selectedProfileActiveBuildCount.value : 0,
    contextSafe: contextSafe.value,
  }),
});
/** Build shows until Records can be reviewed, and while a manifest still needs the reviewer's decision. */
const showBuildWorkspace = computed(
  () =>
    Boolean(currentBuild.value) &&
    (workspaceMode.value === "build" ||
      (workspaceMode.value === "review" && !showReviewWorkspace.value)),
);
/** Publication blockers open review work as one remediation session. */
async function reviewFromPublish(action: () => unknown, code = "") {
  await switchWorkspace("review");
  await action();
  if (!code) return;
  beginQueueRemediation(code);
  if (code === "required_metadata") {
    setReviewWorkspaceMode("record");
    await nextTick();
    focusFirstMetadataBlocker();
  } else if (code === "source_quality" || code === "source_validation") {
    setReviewWorkspaceMode("source");
  } else if (code === "boundary_attention") {
    setReviewWorkspaceMode("record");
    reviewInspectorTab.value = "source";
  } else {
    setReviewWorkspaceMode("record");
  }
}
async function reviewValidationFromPublish() {
  const first = fixIssues.value.find((item) => item?.record_id);
  if (first) {
    await reviewFromPublish(() => fixValidationIssue(first));
    return;
  }
  await reviewFromPublish(() => openValidationIssueQueue(), "metadata_validation");
}

const statusNotices = computed<Notice[]>(() => [
  ...(error.value
    ? [
        {
          id: "error",
          tone: transientNetworkError.value ? ("warning" as const) : ("error" as const),
          text: displayError.value,
        },
      ]
    : []),
  ...(notice.value ? [{ id: "notice", tone: "info" as const, text: notice.value }] : []),
]);
function dismissStatus(id: string) {
  if (id === "error") error.value = "";
  if (id === "notice") notice.value = "";
}
/**
 * Acknowledge build warnings: shown as done at once, recorded on the build (who and when), and published with the
 * corpus. If the save fails the warnings come back, with the reason.
 */
async function acknowledgeBuildWarnings(warnings: string[]) {
  const build = currentBuild.value;
  if (!build || !warnings.length) return;
  const before = build.warning_acknowledgements;
  const pending = Object.fromEntries(
    warnings.map((text, index) => [`pending-${index}-${text.length}`, { warning: text }]),
  );
  currentBuild.value = { ...build, warning_acknowledgements: { ...(before || {}), ...pending } };
  try {
    const saved = await corpusBuilderApi.acknowledgeWarnings(build.build_id, warnings);
    if (currentBuild.value?.build_id === build.build_id)
      currentBuild.value = {
        ...currentBuild.value,
        warning_acknowledgements: saved.warning_acknowledgements,
      };
  } catch (exc) {
    if (currentBuild.value?.build_id === build.build_id)
      currentBuild.value = { ...currentBuild.value, warning_acknowledgements: before };
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  }
}
function setMessage(message: string, tone: "error" | "notice" = "notice") {
  if (tone === "error") {
    error.value = message;
    notice.value = "";
  } else {
    notice.value = message;
    error.value = "";
  }
  void nextTick(() => statusRegion.value?.focus({ preventScroll: true }));
}

function recordMetadata(record: CorpusRecord) {
  return editableRecordMetadata(
    record as unknown as Record<string, unknown>,
    currentBuild.value?.schema || selectedSchema.value,
  );
}
function applyAuthoritativeRecord(record: CorpusRecord, build?: CorpusBuild | null) {
  const id = record.record_id;
  // A later save is already queued and shown optimistically; this older response would briefly revert it.
  // The last response in the queue carries the authoritative state for all of them.
  if (!recordSaveQueue.hasQueuedBehind(id)) {
    applyRecordToQueue(record);
    if (selectedRecordId.value === id) {
      selectedRecord.value = record;
      metadataDraft.value = JSON.stringify(recordMetadata(record), null, 2);
    }
  }
  if (build && currentBuild.value?.build_id === build.build_id) {
    currentBuild.value = build;
    syncBuildInRail(build);
  }
}

function queueRecordRequest(
  recordId: string | readonly string[],
  fields: string[],
  request: (rebase: boolean) => Promise<unknown>,
  onFailure?: () => void,
  retryOnFailure = true,
) {
  recordSaveQueue.enqueue(
    recordId,
    ({ rebase }) => request(rebase),
    (exc) => {
      onFailure?.();
      setMessage(
        i18n.tf("pdf_corpus.record_save_failed", {
          record: typeof recordId === "string" ? recordId : recordId.join(", "),
          fields: fields.join(", "),
          error: exc instanceof Error ? exc.message : String(exc),
        }),
        "error",
      );
    },
    { retryOnFailure },
  );
}
function manageProviders() {
  window.dispatchEvent(
    new CustomEvent("derridai:navigate-native", {
      detail: { path: "/providers", runtimeView: "providers" },
    }),
  );
}
async function switchBuildProvider(profileId: string, modelOverride = "") {
  if (!currentBuild.value || !selectedBuildId.value || !profileId) return;
  busy.value = "profile";
  error.value = "";
  try {
    const direct = directProfilePayload(profileId);
    const payload: Record<string, unknown> = { provider_profile_id: profileId };
    if (modelOverride.trim()) payload.model = modelOverride.trim();
    // Always send the browser endpoint and key. The API uses a stored key only
    // when this request leaves them out.
    if (direct) {
      if (direct.base_url) payload.base_url = direct.base_url;
      if (direct.api_key) payload.api_key = direct.api_key;
      if (!serverProviderIds.value.has(profileId)) {
        for (const key of ["provider", "model", "generation"] as const) {
          if (direct[key] !== undefined) payload[key] = direct[key];
        }
      }
    }
    if (selectedReviewProviderId.value && selectedReviewProviderId.value !== profileId) {
      payload.review_provider_profile_id = selectedReviewProviderId.value;
      const review = directProfilePayload(selectedReviewProviderId.value);
      if (review) {
        const reviewConfig: Record<string, unknown> = {};
        if (review.base_url) reviewConfig.base_url = review.base_url;
        if (review.api_key) reviewConfig.api_key = review.api_key;
        if (!serverProviderIds.value.has(selectedReviewProviderId.value)) {
          for (const key of ["provider", "model", "generation"] as const) {
            if (review[key] !== undefined) reviewConfig[key] = review[key];
          }
        }
        if (Object.keys(reviewConfig).length) payload.review_provider = reviewConfig;
      }
    }
    currentBuild.value = await corpusBuilderApi.switchProviderProfile(
      selectedBuildId.value,
      payload,
    );
    selectedProviderId.value = profileId;
    syncBuildInRail(currentBuild.value);
    const profile = providerProfiles.value.find((item) => item.id === profileId);
    setMessage(
      i18n.tf("pdf_corpus.profile_model_switched", {
        profile: profile?.name || profileId,
        model: modelOverride || profile?.model || "—",
      }),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}

async function refreshCorpusProfiles() {
  try {
    corpusProfiles.value = (await corpusBuilderApi.profiles()).items || [];
  } catch {
    corpusProfiles.value = [];
  }
}
function offerFirstSourceProblem(rows: CorpusQueueRow[]) {
  const first = rows.find(rowHasSourceWarning);
  if (
    first &&
    !sourceWarningsHidden() &&
    sourceProblemDialogBuildId.value !== selectedBuildId.value &&
    !recordSourceWarningOpen.value
  ) {
    sourceProblemDialogBuildId.value = selectedBuildId.value;
    openRecordSourceWarning(first);
  }
}

async function refreshBlocks() {
  const buildId = selectedBuildId.value;
  const assetId = selectedAssetId.value;
  const record = selectedRecord.value;
  const recordId = record?.record_id;
  const ids = [
    ...(record?.source_block_ids || []),
    ...(record?.source_unit_ids || []),
    ...((record?.source_spans || [])
      .map((span) => span.source_unit_id || span.block_id)
      .filter(Boolean) as string[]),
  ]
    .map(String)
    .filter((id, index, all) => all.indexOf(id) === index);
  if (!selectedAssetId.value || !ids.length) {
    sourceBlocks.value = [];
    return;
  }
  const result = await corpusBuilderApi.blocks(assetId, 0, Math.min(1000, ids.length), ids);
  if (
    selectedBuildId.value === buildId &&
    selectedAssetId.value === assetId &&
    selectedRecord.value?.record_id === recordId
  )
    sourceBlocks.value = result.items;
}
async function ensureReviewHydrated(preferredId = "") {
  if (!selectedBuildId.value || !currentBuild.value || awaitingManifestReview.value) return;
  const expected = Number(
    currentBuild.value.record_count || currentBuild.value.metadata_total || 0,
  );
  if (expected < 1) return;
  await nextTick();
  if (recordsLoading.value) return;
  if (
    reviewHydrated.value &&
    expected <= hydratedTopologyCount.value &&
    (!preferredId || preferredId === selectedRecordId.value)
  )
    return;
  // Background topology hydration must reconcile in place. A reset clears the selected
  // Record cache and pagination, which makes live enrichment look like a page refresh.
  await refreshRecords(false, preferredId);
  if (selectedRecord.value && !sourceBlocks.value.length) await refreshBlocks();
}
async function refreshAll() {
  await Promise.all([
    refreshProviders(),
    refreshCorpusProfiles(),
    refreshAssets(),
    refreshBuilds(),
  ]);
  const requestedQueue = String(route.query.queue || "") as ReviewQueue;
  if (
    ["all", "ready", "issues", "metadata", "topology", "source", "accepted", "rejected"].includes(
      requestedQueue,
    )
  )
    reviewQueue.value = requestedQueue;
  await refreshBuild();
  await ensureReviewHydrated(String(route.query.record || ""));
  // A second post-paint hydration closes the lifecycle race where build.json is
  // restored before the records route is available after a hard refresh. This is
  // deliberately independent of any form control interaction.
  window.setTimeout(() => {
    if (hasRecordTopology.value && !reviewHydrated.value) void ensureReviewHydrated();
  }, 250);
}
// Reading the record in context is a per-browser preference.
const showRecordContext = ref(true);
function openRecordPopout() {
  if (!selectedRecord.value) return;
  recordPopout.value = {
    recordId: selectedRecord.value.record_id,
    text: selectedRecord.value.text,
  };
}
try {
  showRecordContext.value = localStorage.getItem("derridai-review-context") !== "off";
} catch {
  // Storage is optional.
}
watch(showRecordContext, (value) => {
  try {
    localStorage.setItem("derridai-review-context", value ? "on" : "off");
  } catch {
    // Storage is optional.
  }
});
/** Jump to a neighbouring record, even if the current queue does not contain it. */
async function selectRecordById(recordId: string) {
  await reviewRecords.selectRecordById(recordId, () => {
    reviewRequested.value = true;
    reviewQueue.value = "all";
  });
}

/** Show a full Record in the review workspace (the queue resolves rows to Records first). */
function activateRecord(record: CorpusRecord) {
  const viewport = captureReviewViewport();
  const sameRecord = selectedRecord.value?.record_id === record.record_id;
  const preserveActiveDraft = sameRecord && editingText.value;
  if (!sameRecord) metadataEditorDirty.value = false;
  selectedRecordId.value = record.record_id;
  selectedRecord.value = record;
  selectedEvidenceField.value = "";
  selectedPdfPage.value = Number(record.pdf_pages?.[0] || 1);
  reviewInspectorTab.value = selectedMetadataBlocked.value ? "metadata" : reviewInspectorTab.value;
  if (!preserveActiveDraft) {
    let saved = "";
    try {
      saved = localStorage.getItem(textDraftKey(selectedBuildId.value, record.record_id)) || "";
    } catch {
      // Best effort: browser storage is optional.
    }
    textDraft.value = saved || String(record.text || "");
    editingText.value = Boolean(saved && saved !== String(record.text || ""));
  }
  resolveSourceOnTextSave.value = Boolean(record.source_quality_issues?.length);
  const fallback = JSON.stringify(recordMetadata(record), null, 2);
  if (!sameRecord || !advancedMetadataDirty.value) {
    try {
      metadataDraft.value =
        localStorage.getItem(metadataDraftKey(selectedBuildId.value, record.record_id)) || fallback;
    } catch {
      metadataDraft.value = fallback;
    }
    advancedMetadataDirty.value = metadataDraft.value !== fallback;
  }

  if (!sameRecord)
    void refreshBlocks().catch((exc: unknown) =>
      setMessage(exc instanceof Error ? exc.message : String(exc), "error"),
    );
  const buildId = selectedBuildId.value;
  if (buildId && !sameRecord)
    void corpusBuilderApi
      .markViewed(buildId, record.record_id)
      .then((result) => {
        if (
          selectedBuildId.value === buildId &&
          selectedRecord.value?.record_id === record.record_id
        )
          selectedRecord.value.activity = result.activity;
      })
      .catch(
        (exc: unknown) =>
          selectedBuildId.value === buildId &&
          setMessage(exc instanceof Error ? exc.message : String(exc), "error"),
      );
  void restoreReviewViewport(viewport, { record: !sameRecord });
}
function toggleReviewSelection(recordId: string, checked: boolean) {
  const next = new Set(selectedReviewIds.value);
  if (checked) next.add(recordId);
  else next.delete(recordId);
  selectedReviewIds.value = next;
}
function toggleVisibleSelection(checked: boolean) {
  const next = new Set(selectedReviewIds.value);
  for (const record of queueRows.value) {
    if (checked) next.add(record.record_id);
    else next.delete(record.record_id);
  }
  selectedReviewIds.value = next;
}
const allVisibleSelected = computed(
  () =>
    queueRows.value.length > 0 &&
    queueRows.value.every((record) => selectedReviewIds.value.has(record.record_id)),
);

function previousSourcePage() {
  if (selectedPdfPageIndex.value > 0)
    selectedPdfPage.value = recordPdfPages.value[selectedPdfPageIndex.value - 1];
}
function nextSourcePage() {
  if (selectedPdfPageIndex.value < recordPdfPages.value.length - 1)
    selectedPdfPage.value = recordPdfPages.value[selectedPdfPageIndex.value + 1];
}

async function useCurrentPdf() {
  const file = runtime.state.pdf.file as File | null;
  if (!file) {
    setMessage(i18n.t("pdf_corpus.open_pdf_first"), "error");
    return;
  }
  await upload(file);
}
function openEnrichmentFromFinish() {
  // Finish actions always mean all records; never inherit a hidden table selection.
  selectedReviewIds.value = new Set();
  llmActionProviderId.value =
    llmActionProviderId.value || selectedProviderId.value || providerProfiles.value[0]?.id || "";
  metadataEnrichmentOpen.value = true;
}
async function chooseBuild(build: CorpusBuild) {
  selectedBuildId.value = build.build_id;
  selectedAssetId.value = build.asset_id;
  selectedRecordId.value = "";
  selectedRecord.value = null;
  sourceBlocks.value = [];
  reviewRecords.clear();
  hydratedMetadataCount.value = 0;
  reviewQueue.value = "all";
  reviewRequested.value = false;
  await router.replace({
    query: {
      ...route.query,
      build: build.build_id,
      record: undefined,
      queue: undefined,
    },
  });
  await refreshBuild();
  await nextTick();
  await refreshRecords(true);
  if (buildRunning.value) startPolling();
}
async function openPdfExplorer() {
  await router.push({ name: "source-explorer", query: route.query });
}
async function reanalyzeDocument() {
  if (!currentBuild.value) return;
  busy.value = "manifest";
  try {
    const result = await corpusBuilderApi.regenerateManifest(
      currentBuild.value.build_id,
      providerPayload.value,
    );
    currentBuild.value = result.build;
    await refreshBuilds();
    if (result.filled.length) await refreshRecords(true);
    setMessage(
      result.filled.length
        ? i18n.tf("pdf_corpus.reanalyze_filled", {
            count: result.filled.length,
            fields: result.filled.join(", "),
          })
        : i18n.t("pdf_corpus.reanalyze_nothing"),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function saveManifest(changes: Record<string, unknown>) {
  if (!currentBuild.value) return;
  busy.value = "manifest";
  try {
    currentBuild.value = await corpusBuilderApi.patchManifest(
      currentBuild.value.build_id,
      changes,
      Number(currentBuild.value.manifest_revision || 1),
    );
    await refreshBuilds();
    await refreshRecords(true);
    setMessage(i18n.t("pdf_corpus.manifest_saved"));
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}

async function startNewBuildSetup() {
  stopPolling();
  selectedBuildId.value = "";
  currentBuild.value = null;
  reviewRecords.clear();
  selectedRecordId.value = "";
  selectedRecord.value = null;
  sourceBlocks.value = [];
  bulkMetadataOpen.value = false;
  void router.replace({
    query: {
      ...route.query,
      workspace: "setup",
      build: undefined,
      record: undefined,
      queue: undefined,
    },
  });
}
function reviewShortcut(event: KeyboardEvent) {
  if (!selectedRecord.value || busy.value) return;
  if (
    (event.ctrlKey || event.metaKey) &&
    !event.altKey &&
    event.key.toLowerCase() === "s" &&
    editingText.value &&
    !focusView.value // Focus View handles its own Ctrl/Cmd+S.
  ) {
    event.preventDefault();
    if (!reviewLocked.value && textDraft.value.trim()) void saveReviewedText();
    return;
  }
  const command = corpusReviewCommandFromKeydown(event);
  if (!command) return;
  event.preventDefault();

  if (command === "accept") void attemptAccept();
  else if (command === "reject") void setDisposition("rejected");
  else if (command === "needs-attention") void setDisposition("pending");
  else if (command === "undo") void undoReview();
  else if (command === "redo") void redoReview();
  else if (command === "next") void focusQueueMove(1);
  else if (command === "previous") void focusQueueMove(-1);
  else if (command === "focus") void toggleReviewFocus();
  else if (command === "metadata" && !focusView.value) {
    if (reviewWorkspaceMode.value === "source") setReviewWorkspaceMode("record");
    focusFirstMetadataBlocker();
  }
}
/**
 * Metadata-queue review is a conveyor: once the current Record has no metadata
 * decisions left, move forward immediately from the optimistic local state.
 * Other review queues keep the existing "Accept & next" handoff because a
 * finished metadata panel does not imply that the Record itself was accepted.
 */
async function handleMetadataComplete() {
  if (reviewQueue.value === "metadata" && selectedRecord.value && !selectedMetadataBlocked.value) {
    await focusQueueMove(1);
    return;
  }
  void nextTick(() => decisionDock.value?.focusAccept());
}
watch(selectedProviderId, (profileId) => {
  if (!profileId) return;
  const payload = directProfilePayload(profileId);
  if (payload?.generation && typeof payload.generation === "object")
    generationOverrides.value = { ...(payload.generation as Record<string, unknown>) };
  const profile = providerProfiles.value.find((item) => item.id === profileId);
  maxConcurrentRequests.value = Math.max(
    1,
    Math.min(16, Number(profile?.max_concurrent_requests || payload?.max_concurrent_requests || 1)),
  );
});
let settingReviewFilters = false;
const advancedMetadataDirty = ref(false);
function trackMetadataSave(request: Promise<unknown>) {
  void request.catch((exc) =>
    setMessage(exc instanceof Error ? exc.message : String(exc), "error"),
  );
}
async function saveAdvancedMetadata() {
  const id = selectedRecordId.value;
  error.value = "";
  await saveMetadata();
  await recordSaveQueue.waitFor(id);
  if (selectedRecordId.value === id && !error.value) advancedMetadataDirty.value = false;
}
function changeReviewQueue(queue: ReviewQueue) {
  reviewQueue.value = queue;
}
function toggleReviewFocus() {
  if (focusView.value) focusView.value = false;
  else openFocusView();
}
async function requestWorkspace(workspace: Parameters<typeof switchWorkspace>[0]) {
  await switchWorkspace(workspace);
}
function setReviewFilters(queue: ReviewQueue, query: string) {
  settingReviewFilters = true;
  reviewQueue.value = queue;
  recordQuery.value = query;
  settingReviewFilters = false;
}
watch(
  [reviewQueue, recordQuery],
  () => {
    if (settingReviewFilters) return;
    if (editingText.value || metadataEditorDirty.value || advancedMetadataDirty.value) {
      // Keep the current draft pinned when the reviewer narrows the queue.
      recordOffset.value = 0;
      void refreshRecords(false);
      return;
    }
    selectedRecordId.value = "";
    selectedRecord.value = null;
    metadataEditorDirty.value = false;
    editingText.value = false;
    recordOffset.value = 0;
    void refreshRecords(false);
  },
  { flush: "sync" },
);
watch([reviewRequested, reviewQueue], ([requested, queue], [wasRequested, wasQueue]) => {
  if (!hasRecordTopology.value || workspaceMode.value === "review") return;
  const explicitReviewNavigation =
    (requested && !wasRequested) || (queue !== "all" && queue !== wasQueue);
  if (explicitReviewNavigation) void switchWorkspace("review");
});
watch(
  () => selectedAsset.value?.media_kind,
  (mediaKind) => {
    if (mediaKind && mediaKind !== "pdf") llmAssessTextNoise.value = false;
  },
);
watch(selectedEvidenceField, (field) => {
  if (!field || !selectedRecord.value) return;
  const ids = allEvidenceBlockIds(selectedRecord.value.metadata_evidence?.[field]);
  const first = sourceBlocks.value.find((block) => ids.includes(block.block_id));
  if (first) selectedPdfPage.value = Number(first.page || selectedPdfPage.value);
});
watch(
  () =>
    [
      currentBuild.value?.build_id,
      currentBuild.value?.record_count,
      currentBuild.value?.metadata_total,
      currentBuild.value?.metadata_enriched_count,
      currentBuild.value?.status,
      currentBuild.value?.stage,
    ] as const,
  async ([buildId, count, metadataTotal, metadataEnriched, status, stage]) => {
    const expected = Math.max(Number(count || 0), Number(metadataTotal || 0));
    // Per-record completion arrives separately over the build WebSocket and patches only
    // that queue row/open Record. Do not re-page the whole review workspace for this counter.
    hydratedMetadataCount.value = Math.max(
      hydratedMetadataCount.value,
      Number(metadataEnriched || 0),
    );
    if (!buildId || expected < 1) return;
    const visibleStage =
      ["constructing_records", "document_intelligence", "enriching", "review", "ready"].includes(
        String(stage || ""),
      ) || ["awaiting_review", "ready"].includes(String(status || ""));
    if (!visibleStage) return;
    if (!reviewHydrated.value || expected > hydratedTopologyCount.value) {
      await ensureReviewHydrated(selectedRecordId.value);
    }
  },
  { flush: "post" },
);
/** Sources handed over from the Sources page or a capture: `/pdf?sources=a,b`. Never starts a build. */
const queuedSourceIds = computed(() =>
  String(route.query.sources || "")
    .split(",")
    .map((id) => id.trim())
    .filter(Boolean),
);
async function queueSources(ids: string[]) {
  await refreshAssets();
  await router.replace({
    query: { ...route.query, mode: "builder", sources: ids.join(",") || undefined },
  });
  configurationSection.value = "source";
}
function viewCaptureSources(captureId: string) {
  window.dispatchEvent(
    new CustomEvent("derridai:navigate-native", {
      detail: { path: `/sources?capture=${encodeURIComponent(captureId)}` },
    }),
  );
}
watch(selectedAssetId, () => {
  if (selectedAssetId.value) void refreshBuilds();
  else configurationSection.value = "source";
});
watch(selectedBuildId, () => {
  sourceProblemDialogBuildId.value = "";
});
watch(
  selectedAsset,
  (asset) => {
    maybeOpenIngestWarning(asset);
  },
  { immediate: true },
);
watch(
  () => route.query.build,
  async (value) => {
    const buildId = String(value || "");
    if (!buildId || buildId === selectedBuildId.value) return;
    selectedBuildId.value = buildId;
    selectedRecordId.value = "";
    selectedRecord.value = null;
    sourceBlocks.value = [];
    const requestedQueue = String(route.query.queue || "") as ReviewQueue;
    if (
      ["all", "ready", "issues", "metadata", "topology", "source", "accepted", "rejected"].includes(
        requestedQueue,
      )
    )
      reviewQueue.value = requestedQueue;
    await refreshBuild();
    await refreshRecords(true, String(route.query.record || ""));
    if (buildRunning.value) startPolling();
  },
);
watch(
  () => route.query.queue,
  (value) => {
    const queue = String(value || "") as ReviewQueue;
    if (
      ["all", "ready", "issues", "metadata", "topology", "source", "accepted", "rejected"].includes(
        queue,
      ) &&
      queue !== reviewQueue.value
    )
      reviewQueue.value = queue;
  },
);
watch(
  () => route.query.record,
  async (value) => {
    const id = String(value || "");
    if (!id || id === selectedRecordId.value) return;
    await refreshRecords(false, id);
  },
);
watch(
  [selectedBuildId, reviewQueue, selectedRecordId, () => route.query.workspace],
  () => {
    if (!selectedBuildId.value) return;
    const query = syncedReviewQuery(route.query, {
      buildId: selectedBuildId.value,
      queue: reviewQueue.value,
      recordId: selectedRecordId.value,
    }) as Record<string, string | undefined>;
    const same =
      String(route.query.build || "") === String(query.build || "") &&
      String(route.query.queue || "") === String(query.queue || "") &&
      String(route.query.record || "") === String(query.record || "");
    if (!same) void router.replace({ query });
  },
  { flush: "post" },
);
watch(
  [
    selectedProviderId,
    selectedReviewProviderId,
    selectedAssetId,
    manualProvider,
    manualModel,
    manualBaseUrl,
    useProfileDefaults,
    generationOverrides,
    stageLimits,
    stageTimeouts,
    recordSizing,
    maxConcurrentRequests,
    enrichmentMode,
    semanticIndexing,
    documentIntelligenceProfile,
    documentNlpProvider,
    documentNlpIncludeEvents,
    autoCleanText,
    llmTouchupDuringEnrichment,
    noiseUnusableThreshold,
    llmAssessTextNoise,
  ],
  persistBuilderDraft,
  { deep: true },
);
watch([reviewQueue, recordQuery, selectedBuildId], () => {
  selectedReviewIds.value = new Set();
});
watch(
  metadataDraft,
  (value) => {
    if (!selectedBuildId.value || !selectedRecordId.value) return;
    try {
      localStorage.setItem(metadataDraftKey(selectedBuildId.value, selectedRecordId.value), value);
    } catch {
      // Best effort: persistence is optional.
    }
  },
  { flush: "post" },
);
watch(
  textDraft,
  (value) => {
    if (!editingText.value || !selectedBuildId.value || !selectedRecordId.value) return;
    try {
      localStorage.setItem(textDraftKey(selectedBuildId.value, selectedRecordId.value), value);
    } catch {
      // Best effort: private browsing may reject storage access.
    }
  },
  { flush: "post" },
);
onMounted(() => {
  window.addEventListener("keydown", reviewShortcut);
  restoreBuilderDraft();
  void loadSchemaChoices();
  void refreshAll()
    .then(() => {
      if (buildRunning.value) startPolling();
    })
    .catch((exc) => setMessage(exc instanceof Error ? exc.message : String(exc), "error"));
});
onBeforeUnmount(() => {
  window.removeEventListener("keydown", reviewShortcut);
  stopPolling();
});
defineExpose({
  saveTextFromFocus,
  saveMetadata,
  setDisposition,
  selectedRecord,
  queueRows,
  error,
});
</script>

<template>
  <section class="corpus-builder" :aria-labelledby="'pdf-corpus-builder-title'">
    <CorpusBuilderWorkspaceHeader
      :source-filename="selectedAsset?.filename || ''"
      :build-id="currentBuild?.build_id || ''"
      :publication-id="currentBuild?.publication?.publication_id || ''"
      :status="primaryStatus"
      :record-count="currentBuild?.record_count || 0"
      :accepted-count="currentBuild?.accepted_count || 0"
      :workspace="workspaceMode"
      :steps="workflowSteps"
      :sticky="!showReviewWorkspace"
      @workspace="requestWorkspace"
    >
      <template #actions>
        <CorpusBuildHistoryMenu
          :builds="builds"
          :total="buildsTotal"
          :selected-build-id="selectedBuildId"
          @select="chooseBuild"
          @refresh="refreshBuilds"
        />
        <a
          v-if="currentBuild?.publication"
          class="btn primary"
          :href="corpusBuilderApi.publicationUrl(currentBuild.publication.publication_id)"
          >{{ i18n.t("pdf_corpus.download_jsonl") }}</a
        >
        <UiButton
          v-if="
            currentBuild &&
            (buildRunning
              ? canStartConcurrentBuild
              : ['cancelled', 'failed', 'interrupted', 'ready', 'awaiting_review'].includes(
                  String(currentBuild.status || ''),
                ))
          "
          :label="
            buildRunning
              ? i18n.t('pdf_corpus.start_concurrent_build')
              : i18n.t('pdf_corpus.start_new_build')
          "
          variant="ghost"
          :disabled="busy !== ''"
          @click="startNewBuildSetup"
        />
      </template>
    </CorpusBuilderWorkspaceHeader>

    <div ref="statusRegion" tabindex="-1" class="status-region" aria-live="polite">
      <UiNoticeStack
        :items="statusNotices"
        :label="i18n.t('pdf_corpus.messages_label')"
        @dismiss="dismissStatus"
        @dismiss-all="error = notice = ''"
      />
    </div>

    <CorpusInitializationDialog
      v-if="workspaceMode === 'build' && currentBuild && buildRunning && !hasRecordTopology"
      :build="currentBuild"
      :disabled="busy !== ''"
      @cancel="cancelBuild"
    />

    <CorpusSetupWorkspace
      v-if="workspaceMode === 'setup'"
      :sections="setupSections"
      :expanded="configurationSection"
      :disabled-sections="selectedAsset ? [] : ['structure']"
      :existing-build-name="currentBuild ? selectedAsset?.filename || currentBuild.build_id : ''"
      @toggle="toggleSetupSection"
    >
      <template #source>
        <CorpusSourceIngest
          v-model:asset-id="selectedAssetId"
          v-model:illegibility="sourceIllegibility"
          v-model:source-url="sourceUrl"
          v-model:gutenberg-query="gutenbergQuery"
          v-model:wikisource-language="wikisourceLanguage"
          :assets="assets"
          :hits="gutenbergHits"
          :wikisource-hits="wikisourceHits"
          :library-searched="librarySearched"
          :library-error="libraryError"
          :library-importing="libraryImporting"
          :library-imported="libraryImported"
          :gutenberg-status="gutenbergStatus"
          :selected-asset="selectedAsset"
          :language-prompt="languagePrompt"
          :disabled="busy === 'upload'"
          :source-selection-disabled="buildRunning"
          :busy="busy"
          @use-current="useCurrentPdf"
          @file="upload"
          @load-url="loadSourceUrl"
          @search-gutenberg="searchGutenberg"
          @search-wikisource="searchWikisource"
          @refresh-gutenberg-status="refreshGutenbergStatus"
          @refresh-gutenberg-catalogue="refreshGutenbergCatalogue"
          @update-gutenberg-archive="updateGutenbergArchive"
          @import-gutenberg="importGutenberg"
          @import-wikisource="importLibraryUrl"
          @delete-asset="deleteAsset"
          @continue="openSetupSection('structure')"
          @save-language="saveSourceLanguage"
          @apply-page-estimate="applyPageEstimate"
          :queued-source-ids="queuedSourceIds"
          @queue-sources="queueSources"
          @sources-changed="refreshAssets"
          @view-capture-sources="viewCaptureSources"
        />
      </template>
      <template #structure>
        <template v-if="paginatedSource && selectedAsset?.pages?.length">
          <CorpusUnitPolicy
            v-if="selectedAsset.media_kind !== 'audio'"
            :asset="selectedAsset"
            :disabled="Boolean(buildRunning && currentBuild?.asset_id === selectedAssetId)"
            :busy="busy === 'units'"
            @apply="applyUnitPolicy"
          />
          <DocumentStructureConfigurator
            class="document-structure-config"
            :asset="selectedAsset"
            :pdf-url="sourcePdfUrl"
            :disabled="
              busy !== '' || Boolean(buildRunning && currentBuild?.asset_id === selectedAssetId)
            "
            :saving="busy === 'document-layout'"
            @save="saveDocumentLayout"
            @save-page-labels="savePageLabels"
          />
        </template>
        <template v-else-if="selectedAsset">
          <CorpusUnitPolicy
            v-if="selectedAsset.media_kind !== 'audio'"
            :asset="selectedAsset"
            :disabled="Boolean(buildRunning && currentBuild?.asset_id === selectedAssetId)"
            :busy="busy === 'units'"
            @apply="applyUnitPolicy"
          />
          <MediaStructureConfigurator
            :media-kind="selectedAsset.media_kind"
            :filename="selectedAsset.filename"
            :page-count="selectedAsset.page_count"
            :block-count="selectedAsset.block_count"
          />
        </template>
        <CorpusTopologyPolicyControl
          v-if="selectedAsset && selectedAsset.media_kind !== 'audio'"
          v-model="topologyPolicy"
          :synthetic-pages-available="syntheticRecordPagesAvailable"
          :disabled="
            Boolean(buildRunning && currentBuild?.asset_id === selectedAssetId) || busy !== ''
          "
        />
        <CorpusRecordSizeAdvice
          v-if="selectedAsset && selectedAsset.media_kind !== 'audio'"
          :asset="selectedAsset"
          :sizing="recordSizing"
          :disabled="
            Boolean(buildRunning && currentBuild?.asset_id === selectedAssetId) || busy !== ''
          "
          @apply="applyUnitPolicy"
        />
        <details class="setup-disclosure">
          <summary>
            <span
              ><b>{{ i18n.t("pdf_corpus.record_construction") }}</b
              ><small>{{
                i18n.tf("pdf_corpus.readiness.sizing", {
                  target: recordSizing.preferred_record_chars.toLocaleString(),
                  tolerance: recordSizing.record_length_tolerance.toLocaleString(),
                })
              }}</small></span
            >
          </summary>
          <div class="setup-disclosure-body">
            <CorpusRecordSizingSettings
              v-model="recordSizing"
              :disabled="busy !== ''"
              :observed="currentBuild?.topology_quality"
            />
          </div>
        </details>
        <div class="setup-continue">
          <UiButton
            variant="primary"
            :label="i18n.t('pdf_corpus.setup.continue_metadata')"
            @click="openSetupSection('metadata')"
          />
        </div>
      </template>
      <template #metadata>
        <CorpusSetupDocumentMetadata
          v-if="selectedAsset"
          :manifest="setupManifest"
          :media-kind="selectedAsset.media_kind"
          :missing-required-count="missingDocumentFields.length"
          :reviewer-override-count="setupDocumentMetadataOverrideCount"
          :disabled="busy !== ''"
          @save="saveSetupManifest"
        />
        <CorpusMetadataConfiguration
          v-model:schema-id="schemaId"
          v-model:run-guidance="runGuidance"
          :schema-choices="schemaChoices"
          :chosen-schema="chosenSchema"
          :run-guidance-fields="runGuidanceFields"
          :disabled="busy !== ''"
          @manage-schemas="schemaEditorOpen = true"
        />
        <div class="setup-continue">
          <UiButton
            variant="primary"
            :label="i18n.t('pdf_corpus.setup.continue_enrichment')"
            @click="openSetupSection('enrichment')"
          />
        </div>
      </template>
      <template #enrichment>
        <CorpusEnrichmentConfiguration
          :selected-provider-id="selectedProviderId"
          :selected-review-provider-id="selectedReviewProviderId"
          :provider-profiles="providerProfiles"
          :default-profile-id="runtime.getDefaultProviderProfileId?.() || ''"
          :selected-provider-label="selectedProviderLabel"
          :selected-profile-model="selectedProfileModel"
          :enrichment-mode="enrichmentMode"
          :semantic-indexing="semanticIndexing"
          :document-intelligence-profile="documentIntelligenceProfile"
          :document-nlp-provider="documentNlpProvider"
          :document-nlp-include-events="documentNlpIncludeEvents"
          :media-kind="selectedAsset?.media_kind || ''"
          :auto-clean-text="autoCleanText"
          :llm-touchup-during-enrichment="llmTouchupDuringEnrichment"
          :noise-unusable-threshold="noiseUnusableThreshold"
          :llm-assess-text-noise="llmAssessTextNoise"
          :manual-provider="manualProvider"
          :manual-model="manualModel"
          :manual-base-url="manualBaseUrl"
          :manual-api-key="manualApiKey"
          :disabled="busy !== ''"
          @update:selected-provider-id="selectedProviderId = $event"
          @update:selected-review-provider-id="selectedReviewProviderId = $event"
          @update:enrichment-mode="enrichmentMode = $event"
          @update:semantic-indexing="semanticIndexing = $event"
          @update:document-intelligence-profile="documentIntelligenceProfile = $event"
          @update:document-nlp-provider="documentNlpProvider = $event"
          @update:document-nlp-include-events="documentNlpIncludeEvents = $event"
          @update:auto-clean-text="autoCleanText = $event"
          @update:llm-touchup-during-enrichment="llmTouchupDuringEnrichment = $event"
          @update:noise-unusable-threshold="noiseUnusableThreshold = $event"
          @update:llm-assess-text-noise="llmAssessTextNoise = $event"
          @update:manual-provider="manualProvider = $event"
          @update:manual-model="manualModel = $event"
          @update:manual-base-url="manualBaseUrl = $event"
          @update:manual-api-key="manualApiKey = $event"
          @manage-providers="manageProviders"
        />
      </template>
      <template #advanced>
        <CorpusAdvancedConfiguration
          v-model:hands-free="handsFree"
          :generation="effectiveGeneration"
          :stage-limits="stageLimits"
          :stage-timeouts="stageTimeouts"
          :max-concurrent-requests="maxConcurrentRequests"
          :use-profile-defaults="useProfileDefaults"
          :disabled="busy !== ''"
          @update:generation="generationOverrides = $event"
          @update:stage-limits="stageLimits = $event"
          @update:stage-timeouts="stageTimeouts = $event"
          @update:max-concurrent-requests="maxConcurrentRequests = $event"
          @update:use-profile-defaults="useProfileDefaults = $event"
        />
      </template>
      <template #footer>
        <CorpusBuildReadiness
          :media-kind="selectedAsset?.media_kind"
          :source-filename="selectedAsset?.filename || ''"
          :page-count="selectedAsset?.page_count || 0"
          :block-count="selectedAsset?.block_count || 0"
          :structure-summary="selectedStructureSummary"
          :topology-summary="topologySummary"
          :provider-label="selectedProviderLabel"
          :model-label="selectedProfileModel || manualModel"
          :enrichment-mode="enrichmentMode"
          :target-chars="recordSizing.preferred_record_chars"
          :tolerance-chars="recordSizing.record_length_tolerance"
          :context-safe="contextSafe"
          :active-build-count="activeBuildCount"
          :can-start="canStartConcurrentBuild"
          :busy="busy === 'build'"
          :issues="setupIssues"
          :schema-label="setupSections[2].summary"
          @build="startBuild"
          @edit-section="openSetupSection"
        />
      </template>
    </CorpusSetupWorkspace>
    <CorpusBuildWorkspace
      v-else-if="showBuildWorkspace && currentBuild"
      :build="currentBuild"
      :running="buildRunning"
      :can-resume="canResume"
      :has-record-topology="hasRecordTopology"
      :ready-count="readyCount"
      :enriching-count="activeEnrichingCount"
      :preparing-count="queuedPreparingCount"
      :attention-count="issueCount"
      :awaiting-manifest-review="awaitingManifestReview"
      :retrying-segmentation="retryingSegmentation"
      :segmentation-needs-review="segmentationNeedsReview"
      :context-safe="contextSafe"
      :busy="busy !== ''"
      :provider-label="activeProviderProfileLabel"
      :model-label="activeModelLabel"
      :run-guidance="activeRunGuidance"
      @pause="pauseBuild"
      @cancel="cancelBuild"
      @resume="resumeBuild"
      @delete="deleteBuild"
      @open-review="switchWorkspace('review')"
      @open-publish="switchWorkspace('publish')"
      @confirm-manifest="confirmManifest"
      @acknowledge-warnings="acknowledgeBuildWarnings"
    >
      <template #manifest>
        <DocumentManifestEditor
          v-if="currentBuild.manifest && Object.keys(currentBuild.manifest).length"
          :media-kind="selectedAsset?.media_kind"
          :manifest="currentBuild.manifest || {}"
          :disabled="buildRunning || busy !== ''"
          @save="saveManifest"
          @reanalyze="reanalyzeDocument"
        />
      </template>
    </CorpusBuildWorkspace>

    <CorpusPublishWorkspace
      v-else-if="workspaceMode === 'publish' && currentBuild"
      :build="currentBuild"
      :busy="busy !== ''"
      :can-publish-unreviewed="canPublishUnreviewed"
      @retry-metadata="retryIncompleteMetadata"
      @review-metadata="reviewFromPublish(openMetadataIssueQueue, 'required_metadata')"
      @review-validation="reviewValidationFromPublish"
      @fix-issue="(issue) => reviewFromPublish(() => fixValidationIssue(issue))"
      @review-topology="reviewFromPublish(openTopologyIssueQueue, 'boundary_attention')"
      @review-issues="reviewFromPublish(openIssueQueue, 'record_attention')"
      @review-rejected="reviewFromPublish(openRejectedQueue)"
      @review-records="reviewFromPublish(openAllReviewQueue, 'review_pending')"
      @review-source="
        reviewFromPublish(
          openSourceIssueQueue,
          publicationBlockerCount('source_validation') ? 'source_validation' : 'source_quality',
        )
      "
      @restore-rejected="restoreAllRejected"
      @start-new="startNewBuildSetup"
      @edit-document-metadata="documentMetadataOpen = true"
      @rerun-enrichment="openEnrichmentFromFinish"
      @publish="publishAndShow()"
      @publish-unreviewed="publishUnreviewed"
    />

    <CorpusReviewWorkspace
      v-else-if="showReviewWorkspace && currentBuild"
      :queue-splitter="queueSplitter"
      :inspector-splitter="inspectorSplitter"
      :height-splitter="reviewHeightSplitter"
      :queue-collapsed="reviewQueueCollapsed"
      :mode="reviewWorkspaceMode"
      :loading="recordsLoading"
      :fix-context="fixContext"
      :fix-progress="fixProgress"
      @fix-next="fixNextIssue"
      @back-to-readiness="returnToReadiness"
      @grid-change="reviewGridEl = $event"
      @frame-change="reviewFrameEl = $event"
    >
      <template #panels>
        <CorpusSemanticWorkspace
          :build-id="currentBuild.build_id"
          :summary="currentBuild.semantic_content_graph"
          :disabled="busy !== '' || buildRunning"
          @refreshed="refreshBuild"
          @changed="refreshBuild"
        />
      </template>
      <template #header>
        <CorpusReviewHeader
          :queue="reviewQueue"
          @update:queue="changeReviewQueue"
          v-model:query="recordQuery"
          :accepted="Number(reviewQueueCounts.accepted ?? currentBuild?.accepted_count ?? 0)"
          :ready="readyCount"
          :issues="issueCount"
          :remaining="pendingCount"
          :review-total="Number(currentBuild?.record_count || 0)"
          :workspace-mode="reviewWorkspaceMode"
          :has-selected-record="Boolean(selectedRecord)"
          :focus-disabled="!selectedRecord"
          :total="Number(currentBuild?.record_count || 0)"
          :metadata="Number(reviewQueueCounts.metadata ?? metadataIssueCount)"
          :topology="topologyIssueCount"
          :source-problems="
            Number(reviewQueueCounts.source ?? currentBuild?.source_problem_count ?? 0)
          "
          :rejected="Number(reviewQueueCounts.rejected ?? currentBuild?.rejected_count ?? 0)"
          :bulk-action-items="bulkActionItems"
          :bulk-action-feedback="bulkActionFeedback"
          :bulk-metadata-open="bulkMetadataOpen"
          :schema="currentBuild?.schema"
          :known-values="metadataKnownValues"
          :region-types="regionTypes"
          :discourse-roles="discourseRoles"
          :selected-count="selectedReviewCount"
          :bulk-total-count="Number(currentBuild?.record_count || recordTotal)"
          :bulk-disabled="busy !== '' || reviewLocked"
          :disabled="busy !== ''"
          @focus="toggleReviewFocus"
          @workspace="setReviewWorkspaceMode"
          @accept-clean="acceptCleanRecords"
          @bulk-action="runBulkAction"
          @bulk-apply="applyBulkMetadata"
          @bulk-close="bulkMetadataOpen = false"
        >
          <template #run-status>
            <CorpusReviewRunStatus
              :build="currentBuild"
              :profiles="providerProfiles"
              :active-profile-id="activeBuildProfileId"
              :active-model="activeModelLabel"
              :disabled="busy !== ''"
              @switch-profile="switchBuildProvider"
              @settle="settleMetadata"
              @cancel="cancelBuild"
              @pause="pauseBuild"
              @resume="resumeBuild"
              @run-another="
                llmActionProviderId =
                  llmActionProviderId || selectedProviderId || providerProfiles[0]?.id || '';
                metadataEnrichmentOpen = true;
              "
              @open-record="openHandsFreeException"
              @inspect-editorial-memory="openEditorialMemory"
              @acknowledge-warnings="acknowledgeBuildWarnings"
            />
          </template>
        </CorpusReviewHeader>
      </template>
      <template #queue>
        <CorpusReviewRecordQueue
          :rows="queueRows"
          :record-total="recordTotal"
          :active-processing-record-ids="activeEnrichingRecordIds"
          :selected-record-id="loadingRecordId || selectedRecordId"
          :selected-review-ids="selectedReviewIds"
          :all-visible-selected="allVisibleSelected"
          :loading="recordsLoading"
          :hydrated="reviewHydrated"
          :queue="reviewQueue"
          :searching="Boolean(recordQuery.trim())"
          :can-open-publish="hasRecordTopology"
          :disabled="busy !== ''"
          :page-number="pageNumber"
          :page-count="pageCount"
          :has-previous-page="recordOffset > 0"
          :has-next-page="recordOffset + pageSize < recordTotal"
          @previous-page="previousPage"
          @next-page="nextPage"
          @root-change="setRecordListElement"
          @collapse="reviewQueueCollapsed = true"
          @toggle-visible="toggleVisibleSelection"
          @toggle-record="toggleReviewSelection"
          @select-record="selectRecord"
          @source-warning="openRecordSourceWarning"
          @show-all="
            reviewQueue = 'all';
            recordQuery = '';
          "
          @open-publish="switchWorkspace('publish')"
        />
      </template>
      <template #record>
        <CorpusReviewRecordPane
          v-model:text-draft="textDraft"
          v-model:show-context="showRecordContext"
          v-model:resolve-source="resolveSourceOnTextSave"
          :record="selectedRecord"
          :loading="Boolean(loadingRecordId)"
          :load-error="recordError"
          :build-id="currentBuild?.build_id || ''"
          :visible="reviewWorkspaceMode === 'record'"
          :queue-collapsed="reviewQueueCollapsed"
          :editing="editingText"
          :busy="busy !== ''"
          :locked="reviewLocked"
          :activity-summary="selectedRecordActivitySummary"
          :popout="recordPopout"
          @root-change="reviewPaneEl = $event"
          @show-queue="reviewQueueCollapsed = false"
          @begin-edit="(touchup) => beginTextEdit(touchup)"
          @cancel-edit="cancelTextEdit"
          @cleanup="textCleanupOpen = true"
          @llm-touchup="llmTouchupOpen = true"
          @save="saveReviewedText()"
          @mark-reviewed="markTextReviewed"
          @open-popout="openRecordPopout"
          @close-popout="recordPopout = null"
          @select-record="selectRecordById"
          @retry="reviewRecords.retryRecord"
        />
      </template>
      <template #inspector>
        <CorpusReviewInspector
          v-model:tab="reviewInspectorTab"
          :mode="reviewWorkspaceMode"
          :has-record="Boolean(selectedRecord)"
          :blocker-count="selectedMetadataBlockingFields.length"
          @back-to-record="setReviewWorkspaceMode('record')"
          @tab-keydown="reviewInspectorKeydown"
          @root-change="reviewInspectorEl = $event"
        >
          <section
            v-if="selectedRecord"
            v-show="
              reviewWorkspaceMode === 'metadata' ||
              (reviewWorkspaceMode === 'record' && reviewInspectorTab === 'metadata')
            "
            id="review-panel-metadata"
            class="review-inspector-panel"
            role="tabpanel"
            aria-labelledby="review-tab-metadata"
            tabindex="0"
          >
            <CorpusMetadataResolutionPanel
              :schema="currentBuild?.schema"
              :build-id="currentBuild?.build_id"
              :record="selectedRecord"
              :region-types="regionTypes"
              :discourse-roles="discourseRoles"
              :busy="reviewLocked || (busy !== '' && busy !== 'metadata-field')"
              :batch-saving="metadataSavingField === '__batch__'"
              :saving-field="metadataSavingField"
              :saved-field="metadataSavedField"
              :confidence-calibration="currentBuild?.llm_confidence_calibration || {}"
              :known-values="metadataKnownValues"
              :blocking-fields="selectedMetadataBlockingFields"
              @complete="handleMetadataComplete"
              @resolve="(field, value) => trackMetadataSave(resolveMetadataField(field, value))"
              @no-value="resolveMetadataNoValue"
              @resolve-many="resolveMetadataSuggestions"
              @source="showMetadataSource"
              @resolve-with-evidence="
                (field, value, text) =>
                  trackMetadataSave(resolveMetadataWithSelectionEvidence(field, value, text))
              "
              @resolve-with-human-source="
                (field, value, note) =>
                  trackMetadataSave(resolveMetadataWithHumanSource(field, value, note))
              "
              @browse-evidence="openEvidenceBrowser"
              @dirty="handleMetadataDirty"
            />
            <CorpusReviewAdvancedMetadata
              v-model:draft="metadataDraft"
              v-model:family="metadataRerunFamily"
              :busy="reviewLocked || busy !== ''"
              :has-manifest="Boolean(currentBuild?.manifest)"
              :profiles="providerProfiles"
              :provider-id="llmActionProviderId || selectedProviderId"
              :model-override="llmActionModel"
              :family-options="metadataFamilyOptions"
              @update:provider-id="(value) => (llmActionProviderId = value)"
              @update:model-override="(value) => (llmActionModel = value)"
              @clear-cache="clearMetadataSuggestionCache"
              @edit-document-metadata="documentMetadataOpen = true"
              @dirty="advancedMetadataDirty = true"
              @save="saveAdvancedMetadata"
              @rerun="rerunMetadata()"
              @requeue="requeueCurrentRecord"
              @enrich-again="
                llmActionProviderId =
                  llmActionProviderId || selectedProviderId || providerProfiles[0]?.id || '';
                metadataEnrichmentOpen = true;
              "
            />
          </section>
          <CorpusReviewEvidencePanel
            v-if="
              selectedRecord &&
              reviewWorkspaceMode === 'record' &&
              reviewInspectorTab === 'evidence'
            "
            :record="selectedRecord"
            :fields="evidenceCandidateFields"
            :build-id="currentBuild?.build_id || ''"
            :llm-request="
              directProfilePayloadWithModel(
                llmActionProviderId || selectedProviderId || providerProfiles[0]?.id || '',
                llmActionModel,
              )
            "
            :selected-field="selectedEvidenceField"
            :blocks="visibleBlocks"
            :evidence-block-ids="evidenceBlockIds"
            :paginated-source="paginatedSource"
            :disabled="busy !== ''"
            @update:selected-field="selectedEvidenceField = $event"
            @toggle-evidence="toggleEvidenceBlock"
            @set-evidence="setEvidenceBlocks"
            @browse-external="openExternalEvidenceBrowser(selectedEvidenceField)"
          />
          <section
            v-else-if="
              selectedRecord &&
              reviewWorkspaceMode === 'record' &&
              reviewInspectorTab === 'semantic'
            "
            id="review-panel-semantic"
            class="review-inspector-panel"
            role="tabpanel"
            aria-labelledby="review-tab-semantic"
            tabindex="0"
          >
            <CorpusRecordSemanticMap
              :build-id="currentBuild?.build_id || ''"
              :record="selectedRecord"
              :disabled="busy !== '' || buildRunning"
              @open-record="navigateToQueueRecord"
              @refreshed="refreshBuild"
            />
          </section>
          <CorpusReviewSourcePanel
            v-else-if="
              selectedRecord &&
              (reviewWorkspaceMode === 'source' ||
                (reviewWorkspaceMode === 'record' && reviewInspectorTab === 'source'))
            "
            :record="selectedRecord"
            :workspace-mode="reviewWorkspaceMode"
            :media-kind="selectedAsset?.media_kind"
            :audio-url="audioSourceUrl"
            :image-url="imageSourceUrl"
            :show-pdf-explorer="selectedSourceCapabilities.pdfViewer"
            :pdf-url="sourcePdfUrl"
            :page="selectedPdfPage"
            :page-count="selectedAsset?.page_count || 0"
            :page-width="selectedPageMeta?.width || 0"
            :page-height="selectedPageMeta?.height || 0"
            :page-blocks="selectedPageBlocks"
            :visible-blocks="visibleBlocks"
            :evidence-ids="evidenceIdsArray"
            :evidence-block-ids="evidenceBlockIds"
            :selected-evidence-field="selectedEvidenceField"
            :paginated-source="paginatedSource"
            :can-previous-source-page="selectedPdfPageIndex > 0"
            :can-next-source-page="selectedPdfPageIndex < recordPdfPages.length - 1"
            :can-merge-previous="canMergePrevious"
            :can-merge-next="canMergeNext"
            :profiles="providerProfiles"
            :provider-profile-id="llmActionProviderId || selectedProviderId"
            :model-override="llmActionModel"
            :active-requests="llmActionConcurrentLoad"
            :disabled="busy !== ''"
            @previous-source-page="previousSourcePage"
            @next-source-page="nextSourcePage"
            @open-viewer="sourceTranscriptionOpen = true"
            @open-pdf-explorer="openPdfExplorer"
            @update:provider-profile-id="llmActionProviderId = $event"
            @update:model-override="llmActionModel = $event"
            @adjudicate="adjudicateBoundaryWithRemediation"
            @toggle-evidence="toggleEvidenceBlock"
            @set-evidence="setEvidenceBlocks"
            @split="split"
          />
          <div v-if="!selectedRecord" class="inspector-empty" role="status">
            {{
              i18n.t(
                loadingRecordId
                  ? "pdf_corpus.record_loading"
                  : recordError
                    ? "pdf_corpus.record_load_failed"
                    : "pdf_corpus.select_record",
              )
            }}
          </div>
        </CorpusReviewInspector>
      </template>
      <template #dock>
        <CorpusRecordDecisionDock
          v-if="selectedRecord"
          ref="decisionDock"
          :accepted="Boolean(selectedRecord.accepted)"
          :editing="editingText"
          :busy="busy !== ''"
          :locked="reviewLocked"
          :saving="busy === 'text'"
          :save-disabled="!textDraft.trim()"
          :blocking-count="selectedMetadataBlockingFields.length"
          :blocking-label="selectedMetadataBlockingLabel"
          :action-items="recordActionItems"
          @focus-blocker="focusFirstMetadataBlocker"
          @undo="undoReview"
          @redo="redoReview"
          @action="runRecordAction"
          @skip="skipRecord"
          @reject="rejectRecord"
          @accept="toggleAccept"
          @cancel-edit="cancelTextEdit"
          @save-text="saveReviewedText()"
        />
      </template>
    </CorpusReviewWorkspace>

    <DocumentManifestDialog
      v-if="documentMetadataOpen && currentBuild?.manifest"
      @reanalyze="reanalyzeDocument"
      :manifest="currentBuild.manifest || {}"
      :disabled="busy !== ''"
      :affected-records="Number(currentBuild.record_count || 0)"
      @save="saveManifest"
      @close="documentMetadataOpen = false"
    />
    <UiDialog
      v-if="missingMetadataPromptOpen"
      size="large"
      :title="i18n.t('pdf_corpus.missing_document_fields_title')"
      :description="i18n.t('pdf_corpus.missing_document_fields_help')"
      :close-label="i18n.t('common.close')"
      @close="missingMetadataPromptOpen = false"
    >
      <CorpusMissingDocumentFields
        v-model="missingDocumentMetadata"
        :fields="missingDocumentFields"
        :disabled="busy !== ''"
      />
      <template #footer>
        <UiButton
          variant="ghost"
          :label="i18n.t('pdf_corpus.missing_document_fields_skip', 'Skip for now')"
          :disabled="busy !== ''"
          @click="continueBuildWithDocumentMetadata()"
        />
        <UiButton
          variant="primary"
          :label="i18n.t('common.continue', 'Continue')"
          :disabled="busy !== '' || !missingMetadataComplete"
          @click="continueBuildWithDocumentMetadata()"
        />
      </template>
    </UiDialog>

    <Teleport to="body"
      ><CorpusBoundarySliceDialog
        v-if="boundarySliceOpen && selectedRecord"
        :text="String(selectedRecord.text || '')"
        :can-previous="canMergePrevious"
        :can-next="canMergeNext"
        :busy="busy !== ''"
        @close="boundarySliceOpen = false"
        @split="split"
        @create="createFromSelection"
    /></Teleport>
    <CorpusTextCleanupDialog
      v-if="textCleanupOpen && selectedRecord"
      :text="textDraft"
      :recurring-lines="recurringCleanupLines"
      :document-terms="cleanupDocumentTerms"
      @close="textCleanupOpen = false"
      @apply="
        (value) => {
          textDraft = value;
          textCleanupOpen = false;
          setMessage(i18n.t('pdf_corpus.cleanup_applied_draft'));
        }
      "
    />
    <CorpusEditorialMemoryDialog
      :open="editorialMemoryOpen"
      :memory="editorialMemory"
      :busy="busy === 'editorial-memory'"
      @close="editorialMemoryOpen = false"
      @reset="resetEditorialMemory"
    />
    <CorpusJsonlPreviewDialog
      :open="jsonlPreviewOpen"
      :jsonl="jsonlPreview.jsonl"
      :validation-errors="jsonlPreview.validation_errors"
      :unresolved-fields="jsonlPreview.unresolved_fields"
      :would-publish="jsonlPreview.would_publish"
      :busy="busy !== ''"
      @close="jsonlPreviewOpen = false"
    />
    <CorpusLlmTextTouchupDialog
      :open="llmTouchupOpen"
      :source-text="textDraft || selectedRecord?.text || ''"
      :proposed-text="llmTouchupResult.proposed_text"
      :changes="llmTouchupResult.changes"
      :warnings="llmTouchupResult.warnings"
      :provider="llmTouchupResult.provider"
      :model="llmTouchupResult.model"
      :proposal-id="llmTouchupResult.proposal_id"
      :run-id="llmTouchupResult.run_id"
      :proposal-created-at="llmTouchupResult.created_at"
      :proposal-status="llmTouchupResult.status"
      :no-change="llmTouchupResult.no_change"
      :error="llmTouchupError"
      :busy="busy === 'text-touchup'"
      :profiles="providerProfiles"
      :provider-profile-id="llmActionProviderId"
      :model-override="llmActionModel"
      :concurrency-risk="
        Boolean(
          providerProfiles.find((p) => p.id === llmActionProviderId)?.type === 'ollama' &&
            llmActionConcurrentLoad + 1 >
              Number(
                providerProfiles.find((p) => p.id === llmActionProviderId)
                  ?.max_concurrent_requests || 1,
              ),
        )
      "
      :active-requests="llmActionConcurrentLoad"
      :concurrency-limit="
        Number(
          providerProfiles.find((p) => p.id === llmActionProviderId)?.max_concurrent_requests || 1,
        )
      "
      :record-id="selectedRecord?.record_id"
      @update:provider-profile-id="(value) => (llmActionProviderId = value)"
      @update:model-override="(value) => (llmActionModel = value)"
      @close="llmTouchupOpen = false"
      @run="runLlmTouchup"
      @apply="applyLlmTouchup"
      @dismiss="dismissLlmTouchup"
    />
    <SourceTranscriptionDialog
      :media-kind="selectedAsset?.media_kind"
      :audio-url="audioSourceUrl"
      :image-url="imageSourceUrl"
      v-if="selectedRecord && selectedAsset"
      :open="sourceTranscriptionOpen"
      :pdf-url="sourcePdfUrl"
      :page="selectedPdfPage"
      :page-count="selectedAsset.page_count"
      :printed-page="selectedRecord.page_start"
      :page-width="selectedPageMeta?.width || 0"
      :page-height="selectedPageMeta?.height || 0"
      :blocks="selectedPageBlocks"
      :text="String(selectedRecord.text || '')"
      :busy="busy !== ''"
      @close="sourceTranscriptionOpen = false"
      @page-change="(page) => (selectedPdfPage = page)"
      @save-text="saveSourceTranscription"
    />
    <CorpusSourceQualityDialog
      :open="ingestWarningOpen"
      :extraction-noise="selectedAsset?.extraction_noise"
      @close="acknowledgeIngestWarning"
    />
    <CorpusSourceQualityDialog
      :open="recordSourceWarningOpen && Boolean(selectedRecord?.source_quality_issues?.length)"
      :issues="selectedRecord?.source_quality_issues"
      @close="acknowledgeRecordSourceWarning"
      @edit-text="
        recordSourceWarningOpen = false;
        beginTextEdit();
      "
      @open-source="
        recordSourceWarningOpen = false;
        reviewInspectorTab = 'source';
      "
    />
    <UiDialog
      v-if="schemaEditorOpen"
      size="xlarge"
      :title="i18n.t('schemas.manage_title')"
      :description="i18n.t('schemas.manage_help')"
      :close-label="i18n.t('ui.close')"
      @close="schemaEditorOpen = false"
    >
      <MetadataSchemaEditor
        :provider-profiles="providerProfiles"
        :default-provider-id="runtime.getDefaultProviderProfileId?.() || ''"
        @changed="loadSchemaChoices"
        @saved="
          (id) => {
            schemaId = id;
          }
        "
      />
      <template #footer>
        <UiButton size="small" @click="openSchemasPage">
          {{ i18n.t("schemas.open_page", "Open as a page") }}
        </UiButton>
      </template>
    </UiDialog>
    <UiDialog
      v-if="handsFreeOpen"
      size="medium"
      :title="i18n.t('pdf_corpus.run_hands_free_title')"
      :description="i18n.t('pdf_corpus.run_hands_free_help')"
      :close-label="i18n.t('ui.close')"
      @close="handsFreeOpen = false"
    >
      <CorpusHandsFreeSettings v-model="handsFree" :disabled="busy !== ''" :show-enable="false" />
      <template #footer
        ><UiButton @click="handsFreeOpen = false"> {{ i18n.t("ui.cancel") }}</UiButton
        ><UiButton variant="primary" :disabled="busy !== ''" @click="runHandsFree">
          {{ i18n.t("pdf_corpus.run_hands_free_action") }}
        </UiButton></template
      >
    </UiDialog>
    <MetadataEnrichmentDialog
      :groups="currentBuild?.schema?.groups?.map((g) => ({ key: g.key, label: g.label }))"
      :open="metadataEnrichmentOpen"
      :profiles="providerProfiles"
      :provider-profile-id="llmActionProviderId"
      :model-override="llmActionModel"
      :busy="busy === 'metadata-enrichment'"
      :record-count="currentBuild?.record_count || 0"
      :accepted-count="currentBuild?.accepted_count || 0"
      :selected-count="selectedReviewIds.size"
      :selected-record-ids="[...selectedReviewIds]"
      @update:provider-profile-id="(value) => (llmActionProviderId = value)"
      @update:model-override="(value) => (llmActionModel = value)"
      @close="metadataEnrichmentOpen = false"
      @run="runMetadataEnrichment"
    />
    <CorpusEvidenceBrowserDialog
      v-if="evidenceBrowser && selectedRecord && selectedAssetId"
      :asset-id="selectedAssetId"
      :around-block-id="String(selectedRecord.source_block_ids?.[0] || '')"
      :record-block-ids="(selectedRecord.source_block_ids || []).map(String)"
      :field-label="
        i18n.t(`record.${evidenceBrowser.field}`, evidenceBrowser.field.replaceAll('_', ' '))
      "
      :initial-chosen="
        evidenceBrowser.evidenceOnly
          ? (
              selectedRecord.metadata_evidence?.[evidenceBrowser.field]?.external_block_ids || []
            ).map(String)
          : []
      "
      @close="evidenceBrowser = null"
      @confirm="confirmExternalEvidence"
    />
    <Teleport to="body"
      ><CorpusRecordFocusReview
        v-if="focusView && selectedRecord"
        v-model:show-context="showRecordContext"
        v-model:inspector-tab="reviewInspectorTab"
        :record="selectedRecord"
        :build-id="currentBuild?.build_id || ''"
        :evidence-llm-request="
          directProfilePayloadWithModel(
            llmActionProviderId || selectedProviderId || providerProfiles[0]?.id || '',
            llmActionModel,
          )
        "
        :schema="currentBuild?.schema"
        :busy="busy !== ''"
        :locked="reviewLocked"
        :region-types="regionTypes"
        :discourse-roles="discourseRoles"
        :confidence-calibration="currentBuild?.llm_confidence_calibration || {}"
        :known-values="metadataKnownValues"
        :blocking-fields="selectedMetadataBlockingFields"
        :saving-field="metadataSavingField"
        :saved-field="metadataSavedField"
        :batch-saving="metadataSavingField === '__batch__'"
        :action-items="recordActionItems"
        :accepted="Number(currentBuild?.accepted_count || 0)"
        :remaining="pendingCount"
        :total="Number(currentBuild?.record_count || 0)"
        :can-history-back="focusHistoryIndex > 0"
        :can-history-forward="focusHistoryIndex >= 0 && focusHistoryIndex < focusHistory.length - 1"
        :can-previous-record="selectedRecordIndex > 0 || recordOffset > 0"
        :can-next-record="
          selectedRecordIndex >= 0 &&
          (selectedRecordIndex < queueRows.length - 1 || recordOffset + pageSize < recordTotal)
        "
        :editing-text="editingText"
        :text-draft="textDraft"
        :resolve-source-issues="resolveSourceOnTextSave"
        :evidence-fields="evidenceCandidateFields"
        :selected-evidence-field="selectedEvidenceField"
        :evidence-block-ids="evidenceIdsArray"
        :paginated-source="paginatedSource"
        :source-blocks="visibleBlocks"
        :source-page-blocks="selectedPageBlocks"
        :media-kind="selectedAsset?.media_kind"
        :audio-url="audioSourceUrl"
        :image-url="imageSourceUrl"
        :show-pdf-explorer="selectedSourceCapabilities.pdfViewer"
        :source-pdf-url="sourcePdfUrl"
        :source-pdf-page="selectedPdfPage"
        :source-pdf-page-count="selectedAsset?.page_count || 0"
        :source-page-width="selectedPageMeta?.width || 0"
        :source-page-height="selectedPageMeta?.height || 0"
        :can-previous-source-page="selectedPdfPageIndex > 0"
        :can-next-source-page="selectedPdfPageIndex < recordPdfPages.length - 1"
        :can-merge-previous="canMergePrevious"
        :can-merge-next="canMergeNext"
        :provider-profiles="providerProfiles"
        :llm-provider-profile-id="llmActionProviderId || selectedProviderId"
        :llm-model-override="llmActionModel"
        :active-requests="llmActionConcurrentLoad"
        :just-processed-record-id="justProcessedRecordId"
        :next-record-id="nextQueueRecordId"
        @close="toggleReviewFocus"
        @history-back="focusHistoryMove(-1)"
        @history-forward="focusHistoryMove(1)"
        @previous-record="focusQueueMove(-1)"
        @next-record="focusQueueMove(1)"
        @record-action="runRecordAction"
        @focus-blocker="focusFirstMetadataBlocker"
        @open-source-issue="recordSourceWarningOpen = true"
        @begin-text-edit="beginTextEdit"
        @cancel-text-edit="cancelTextEdit"
        @save-text="saveReviewedText()"
        @mark-text-reviewed="markTextReviewed"
        @text-draft-change="textDraft = $event"
        @resolve-source-issues-change="resolveSourceOnTextSave = $event"
        @open-text-cleanup="textCleanupOpen = true"
        @resolve-metadata="(field, value) => trackMetadataSave(resolveMetadataField(field, value))"
        @resolve-metadata-with-evidence="
          (field, value, text) =>
            trackMetadataSave(resolveMetadataWithSelectionEvidence(field, value, text))
        "
        @resolve-metadata-with-human-source="
          (field, value, note) =>
            trackMetadataSave(resolveMetadataWithHumanSource(field, value, note))
        "
        @browse-metadata-evidence="openEvidenceBrowser"
        @resolve-metadata-many="resolveMetadataSuggestions"
        @confirm-no-metadata-value="resolveMetadataNoValue"
        @metadata-dirty="handleMetadataDirty"
        @metadata-complete="handleMetadataComplete"
        @llm-touchup="openLlmTouchup"
        @accept="toggleAccept"
        @reject="rejectRecord"
        @skip="skipRecord"
        @undo="undoReview"
        @redo="redoReview"
        @update-llm-provider-profile="(value) => (llmActionProviderId = value)"
        @update-llm-model="(value) => (llmActionModel = value)"
        @adjudicate-boundary="adjudicateBoundary"
        @open-source-viewer="sourceTranscriptionOpen = true"
        @open-pdf-explorer="openPdfExplorer"
        @previous-source-page="previousSourcePage"
        @next-source-page="nextSourcePage"
        @split-after="split"
        @select-evidence="selectedEvidenceField = $event"
        @toggle-evidence="toggleEvidenceBlock"
        @set-evidence="setEvidenceBlocks"
        @browse-external-evidence="openExternalEvidenceBrowser"
        @navigate-record="navigateToQueueRecord"
    /></Teleport>
  </section>
</template>

<style scoped src="../features/corpus-builder/CorpusBuilderShell.css"></style>
