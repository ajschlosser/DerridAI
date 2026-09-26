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
import CorpusBuildProgress from "./CorpusBuildProgress.vue";
import FieldEvidenceList from "./FieldEvidenceList.vue";
import DocumentStructureConfigurator from "./DocumentStructureConfigurator.vue";
import MediaStructureConfigurator from "./MediaStructureConfigurator.vue";
import SourceTranscriptionDialog from "./SourceTranscriptionDialog.vue";
import { sourceMediaCapabilities, timeLabel } from "../domain/sourceMedia";
import CorpusSourceSummary from "./CorpusSourceSummary.vue";
import DocumentManifestEditor from "./DocumentManifestEditor.vue";
import DocumentManifestDialog from "./DocumentManifestDialog.vue";
import CorpusInitializationDialog from "./CorpusInitializationDialog.vue";
import CorpusWorkflowStepper from "./CorpusWorkflowStepper.vue";
import CorpusBuildReadiness from "./CorpusBuildReadiness.vue";
import CorpusSourceIngest from "./CorpusSourceIngest.vue";
import CorpusBuildHistoryMenu from "./CorpusBuildHistoryMenu.vue";
import CorpusQualitySummary from "./CorpusQualitySummary.vue";
import CorpusRecordSizingSettings from "./CorpusRecordSizingSettings.vue";
import CorpusRecordFocusReview from "./CorpusRecordFocusReview.vue";
import CorpusReviewQueueTabs from "./CorpusReviewQueueTabs.vue";
import type { ReviewQueue } from "../types/corpus";
import CorpusBuildLifecycleCard from "./CorpusBuildLifecycleCard.vue";
import CorpusMetadataIssues from "./CorpusMetadataIssues.vue";
import CorpusBuildTimeline from "./CorpusBuildTimeline.vue";
import CorpusFinishWorkspace from "./CorpusFinishWorkspace.vue";
import CorpusMetadataResolutionPanel from "./CorpusMetadataResolutionPanel.vue";
import CorpusBuildStageNotice from "./CorpusBuildStageNotice.vue";
import CorpusSourceQualityDialog from "./CorpusSourceQualityDialog.vue";
import CorpusBulkMetadataEditor from "./CorpusBulkMetadataEditor.vue";
import CorpusTextCleanupDialog from "./CorpusTextCleanupDialog.vue";
import CorpusEditorialMemoryDialog from "./CorpusEditorialMemoryDialog.vue";
import CorpusReviewSessionBar from "./CorpusReviewSessionBar.vue";
import CorpusRevisionHistory from "./CorpusRevisionHistory.vue";
import CorpusJsonlPreviewDialog from "./CorpusJsonlPreviewDialog.vue";
import CorpusLlmTextTouchupDialog from "./CorpusLlmTextTouchupDialog.vue";
import CorpusBoundarySliceDialog from "./CorpusBoundarySliceDialog.vue";
import CorpusBoundaryAdjudication from "./CorpusBoundaryAdjudication.vue";
import MetadataEnrichmentDialog from "./MetadataEnrichmentDialog.vue";
import CorpusModelActivity from "./CorpusModelActivity.vue";
import CorpusHandsFreeSettings from "./CorpusHandsFreeSettings.vue";
import MetadataSchemaEditor from "./MetadataSchemaEditor.vue";
import {
  metadataSchemasApi,
  type MetadataSchema,
  type SchemaSummary,
} from "../api/metadataSchemas";
import UiDialog from "./ui/UiDialog.vue";
import LlmExecutionControl from "./LlmExecutionControl.vue";
import { useCorpusBuildLifecycle } from "../composables/useCorpusBuildLifecycle";
import { usePdfCorpusPaneSizing } from "../composables/usePdfCorpusPaneSizing";
import { useCorpusIngestWarning } from "../composables/useCorpusIngestWarning";
import { useCorpusRunGuidance } from "../composables/useCorpusRunGuidance";
import { useCorpusReviewWorkspace } from "../features/corpus-builder/composables/useCorpusReviewWorkspace";
import { useCorpusSourceConfiguration } from "../features/corpus-builder/composables/useCorpusSourceConfiguration";
import { useCorpusProviderConfiguration } from "../features/corpus-builder/composables/useCorpusProviderConfiguration";
import { useCorpusBuildLifecycleController } from "../features/corpus-builder/composables/useCorpusBuildLifecycleController";
import { useCorpusReviewNavigation } from "../features/corpus-builder/composables/useCorpusReviewNavigation";
import { useCorpusReviewDecisions } from "../features/corpus-builder/composables/useCorpusReviewDecisions";
import { useCorpusTextReview } from "../features/corpus-builder/composables/useCorpusTextReview";
import { useCorpusMetadataReview } from "../features/corpus-builder/composables/useCorpusMetadataReview";
import { useCorpusBoundaryReview } from "../features/corpus-builder/composables/useCorpusBoundaryReview";
import { corpusReviewCommandFromKeydown } from "../features/corpus-builder/domain/reviewCommands";
import {
  editableRecordMetadata,
  evidenceCandidateFieldNames,
  reviewableMetadataFieldNames,
} from "../features/corpus-builder/domain/recordMetadata";
import { useCorpusPublication } from "../features/corpus-builder/composables/useCorpusPublication";
import AppIcon from "./AppIcon.vue";
import CorpusRunMonitor from "./corpus-builder/CorpusRunMonitor.vue";
import CorpusConfigurationNav, {
  type CorpusConfigurationSection,
} from "./corpus-builder/CorpusConfigurationNav.vue";
import CorpusBuilderWorkspaceHeader from "./corpus-builder/CorpusBuilderWorkspaceHeader.vue";
import CorpusReviewRecordQueue from "./corpus-builder/CorpusReviewRecordQueue.vue";
import CorpusEnrichmentConfiguration from "./corpus-builder/CorpusEnrichmentConfiguration.vue";
import CorpusMetadataConfiguration from "./corpus-builder/CorpusMetadataConfiguration.vue";
import CorpusAdvancedConfiguration from "./corpus-builder/CorpusAdvancedConfiguration.vue";
import CorpusActionMenu, { type CorpusActionMenuItem } from "./CorpusActionMenu.vue";
import { recordIssueKinds } from "../domain/corpusReview";
import { RecordMutationQueue } from "../domain/recordMutationQueue";
import {
  firstRecordWithSourceWarning,
  hideSourceWarnings,
  sourceWarningsHidden,
} from "../domain/sourceQuality";
import { recurringShortLines } from "../domain/textCleanup";
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
const records = ref<CorpusRecord[]>([]);
const recordTotal = ref(0);
const recordOffset = ref(0);
const pageSize = 50;
const selectedRecordId = ref("");
const selectedRecord = ref<CorpusRecord | null>(null);
const justProcessedRecordId = ref("");
const sourceBlocks = ref<SourceBlock[]>([]);
const selectedEvidenceField = ref("");
const selectedPdfPage = ref(1);
const reviewQueue = ref<ReviewQueue>("all");
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
    schemaChoices.value = (await metadataSchemasApi.list()).items;
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
const recordsLoading = ref(false);
const reviewHydrated = ref(false);
const hydratedTopologyCount = ref(0);
const hydratedMetadataCount = ref(0);
let recordRequestSerial = 0;
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
  gutenbergStatus,
  lastIngestedAsset,
  refreshAssets,
  upload,
  loadSourceUrl,
  searchGutenberg,
  searchWikisource,
  refreshGutenbergStatus,
  refreshGutenbergCatalogue,
  updateGutenbergArchive,
  importGutenberg,
  savePageLabels,
  saveDocumentLayout,
} = useCorpusSourceConfiguration(busy, setMessage);
const error = ref("");
const notice = ref("");
const statusRegion = ref<HTMLElement | null>(null);
const acceptButtonEl = ref<HTMLButtonElement | null>(null);
const configurationSection = ref<CorpusConfigurationSection>("source");
const recordSaveQueue = new RecordMutationQueue();
const documentMetadataOpen = ref(false);
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
  records,
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
  metadataFieldIssueCount,
  metadataRetryRunning,
  awaitingManifestReview,
  hasRecordTopology,
  showBuildConfiguration,
  finishPhase,
  showReviewWorkspace,
} = useCorpusBuildLifecycle(currentBuild, recordTotal, reviewQueue);
const {
  registerBuildOperation,
  syncBuildInRail,
  refreshBuilds,
  refreshBuild,
  startPolling,
  stopPolling,
  startBuild,
  resumeBuild,
  retryIncompleteMetadata,
  confirmManifest,
  cancelBuild,
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
  applyBuildRequest,
  setMessage,
  resetReviewForBuildStart: () => {
    reviewHydrated.value = false;
    hydratedTopologyCount.value = 0;
    hydratedMetadataCount.value = 0;
    records.value = [];
    recordTotal.value = 0;
    selectedRecord.value = null;
    sourceBlocks.value = [];
  },
  refreshRecords,
  t: (key, fallback) => i18n.t(key, fallback),
  tf: (key, values) => i18n.tf(key, values),
});

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
  rememberMetadataValues,
  saveMetadata,
  assignEvidenceBlock,
  toggleEvidenceBlock,
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
  records,
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

async function assignSelectedMetadataEvidence(field: string, selectedText: string) {
  const selected = selectedText.replace(/\s+/g, " ").trim().toLocaleLowerCase();
  if (!selectedRecord.value || !selected) return;
  const allowedIds = new Set((selectedRecord.value.source_block_ids || []).map(String));
  const candidates = sourceBlocks.value.filter((block) => allowedIds.has(String(block.block_id)));
  let block =
    candidates.find((item) =>
      String(item.text || "")
        .replace(/\s+/g, " ")
        .toLocaleLowerCase()
        .includes(selected),
    ) || null;
  if (!block) {
    const wanted = normalizedEvidenceWords(selected);
    let score = 0;
    for (const item of candidates) {
      const words = normalizedEvidenceWords(String(item.text || ""));
      const overlap = [...wanted].filter((word) => words.has(word)).length;
      const next = wanted.size ? overlap / wanted.size : 0;
      if (next > score) {
        score = next;
        block = item;
      }
    }
    if (score < 0.45) block = null;
  }
  if (!block?.block_id) {
    showMetadataSource(field);
    return;
  }
  await assignEvidenceBlock(field, String(block.block_id));
  selectedEvidenceField.value = field;
  reviewInspectorTab.value = "evidence";
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
      maxConcurrentRequests.value = Math.max(1, Math.min(16, Number(draft.maxConcurrentRequests)));
    if (draft.enrichmentMode === "fast" || draft.enrichmentMode === "deep")
      enrichmentMode.value = draft.enrichmentMode;
    if (typeof draft.semanticIndexing === "boolean")
      semanticIndexing.value = draft.semanticIndexing;
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

function openRecordSourceWarning(record: CorpusRecord) {
  selectRecord(record);
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
    return new Set((info?.block_ids || []).map(String));
  }
  return new Set(
    Object.values(selectedRecord.value.metadata_evidence || {}).flatMap((info) =>
      (info.block_ids || []).map(String),
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
  const ids = new Set(selectedRecord.value?.source_block_ids || []);
  return sourceBlocks.value.filter((block) => ids.has(block.block_id));
});
const recurringCleanupLines = computed(() =>
  recurringShortLines(
    records.value.map((row) => String(row.text || "")),
    3,
  ),
);
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
  records.value.findIndex((row) => row.record_id === selectedRecordId.value),
);
const {
  boundarySliceOpen,
  canMergePrevious,
  canMergeNext,
  mergeUnavailable,
  sliceUnavailable,
  merge,
  split,
  sliceRecord,
  adjudicateBoundary,
} = useCorpusBoundaryReview({
  currentBuild,
  selectedRecord,
  selectedRecordId,
  records,
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
  reviewMetadataRecord,
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
  currentBuild,
  records,
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
});
const nextQueueRecordId = computed(() => {
  const index = selectedRecordIndex.value;
  return index >= 0 ? records.value[index + 1]?.record_id || "" : "";
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
const canStartConcurrentBuild = computed(() =>
  Boolean(
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
const selectedSourceCapabilities = computed(() =>
  sourceMediaCapabilities(selectedAsset.value?.media_kind),
);
// Printed-page mapping is a source capability, not a synonym for "has pages".
const paginatedSource = computed(() => selectedSourceCapabilities.value.printedPagination);
const imageSourceUrl = computed(() =>
  selectedSourceCapabilities.value.imageViewer && selectedAssetId.value
    ? corpusBuilderApi.assetContentUrl(selectedAssetId.value)
    : "",
);
const audioSourceUrl = computed(() =>
  selectedSourceCapabilities.value.audioPlayer && selectedAssetId.value
    ? corpusBuilderApi.assetContentUrl(selectedAssetId.value)
    : "",
);
const sourcePdfUrl = computed(() =>
  selectedSourceCapabilities.value.pdfViewer && selectedAssetId.value
    ? corpusBuilderApi.assetContentUrl(selectedAssetId.value)
    : "",
);
const recordPdfPages = computed(() =>
  Array.from(
    new Set((selectedRecord.value?.pdf_pages || []).map(Number).filter((value) => value > 0)),
  ).sort((a, b) => a - b),
);
const selectedPdfPageIndex = computed(() =>
  Math.max(0, recordPdfPages.value.indexOf(selectedPdfPage.value)),
);
const selectedPageMeta = computed(
  () =>
    selectedAsset.value?.pages?.find(
      (page) => Number(page.pdf_page) === Number(selectedPdfPage.value),
    ) || null,
);
const selectedPageBlocks = computed(() =>
  visibleBlocks.value.filter(
    (block) => !paginatedSource.value || Number(block.page) === Number(selectedPdfPage.value),
  ),
);
const evidenceIdsArray = computed(() => Array.from(evidenceBlockIds.value));
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
  acceptFromFocus,
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
  records,
  recordTotal,
  reviewQueue,
  recordQuery,
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
const setupWarnings = computed(() => {
  const warnings: string[] = [];
  if (
    paginatedSource.value &&
    selectedAsset.value?.pages?.length &&
    !selectedAsset.value.document_layout?.main_text_pdf_start
  )
    warnings.push(i18n.t("pdf_corpus.readiness.review_structure"));
  if (selectedProviderId.value && selectedProfileActiveBuildCount.value)
    warnings.push(
      i18n.tf("pdf_corpus.profile_active_builds", {
        count: selectedProfileActiveBuildCount.value,
      }),
    );
  return warnings;
});

function formatDate(value?: string | null) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(i18n.locale || undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}
function statusLabel(build: CorpusBuild) {
  if (build.publication) return i18n.t("pdf_corpus.status.published_snapshot");
  return i18n.t(
    `pdf_corpus.status.${String(build.status || "unknown")}`,
    String(build.status || "unknown").replace(/_/g, " "),
  );
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
  const index = records.value.findIndex((item) => item.record_id === id);
  if (index >= 0) records.value.splice(index, 1, record);
  if (selectedRecordId.value === id) {
    selectedRecord.value = record;
    metadataDraft.value = JSON.stringify(recordMetadata(record), null, 2);
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
async function refreshRecords(reset = false, preferredId = "") {
  if (reset) recordOffset.value = 0;
  if (!selectedBuildId.value) {
    records.value = [];
    metadataObservedValues.value = {};
    recordTotal.value = 0;
    selectedRecord.value = null;
    reviewHydrated.value = false;
    hydratedTopologyCount.value = 0;
    return;
  }
  const requestId = ++recordRequestSerial;
  recordsLoading.value = true;
  try {
    const expected = Number(
      currentBuild.value?.record_count || currentBuild.value?.metadata_total || 0,
    );
    let result: {
      items: CorpusRecord[];
      total: number;
      offset: number;
      limit: number;
      queue_counts?: CorpusBuild["review_queue_counts"];
      metadata_values?: Record<string, string[]>;
    } = { items: [], total: 0, offset: recordOffset.value, limit: pageSize };
    // Record persistence can become visible a fraction after build.json on a refresh.
    // Hydrate independently of form interaction and retry the read while the build
    // explicitly advertises topology that should already exist.
    for (let attempt = 0; attempt < 5; attempt++) {
      result = await corpusBuilderApi.records(
        selectedBuildId.value,
        recordOffset.value,
        pageSize,
        reviewQueue.value,
        recordQuery.value,
      );
      if (
        result.total > 0 ||
        expected === 0 ||
        reviewQueue.value !== "all" ||
        Boolean(recordQuery.value)
      )
        break;
      await new Promise((resolve) => window.setTimeout(resolve, 120 * (attempt + 1)));
      if (requestId !== recordRequestSerial) return;
    }
    if (requestId !== recordRequestSerial) return;
    if (result.queue_counts && currentBuild.value)
      currentBuild.value = { ...currentBuild.value, review_queue_counts: result.queue_counts };
    metadataObservedValues.value = result.metadata_values || {};
    records.value = result.items;
    recordTotal.value = result.total;
    reviewHydrated.value = true;
    const firstSourceProblem = firstRecordWithSourceWarning(result.items);
    if (
      firstSourceProblem &&
      !sourceWarningsHidden() &&
      sourceProblemDialogBuildId.value !== selectedBuildId.value &&
      !recordSourceWarningOpen.value
    ) {
      sourceProblemDialogBuildId.value = selectedBuildId.value;
      openRecordSourceWarning(firstSourceProblem);
    }
    const filteredRecordView = reviewQueue.value !== "all" || Boolean(recordQuery.value);
    if (result.total > 0 || expected === 0 || filteredRecordView)
      // A zero-row filtered queue is still a successful hydration. Track the
      // build's advertised topology, not the filtered row count, or an empty
      // "issues" queue will be fetched again on every build-status poll.
      hydratedTopologyCount.value = Math.max(hydratedTopologyCount.value, expected, result.total);
    const wanted = preferredId || selectedRecordId.value;
    const match = wanted ? records.value.find((row) => row.record_id === wanted) : undefined;
    const preserveDraft = Boolean(
      selectedRecord.value &&
        selectedRecordId.value === wanted &&
        (editingText.value || metadataEditorDirty.value),
    );
    if (match && !preserveDraft) {
      selectRecord(match);
      return;
    }
    if (match && preserveDraft) {
      return;
    }
    // Background queue growth/filter churn must never replace the record the
    // reviewer is actively working on. Explicit queue/search navigation clears
    // selectedRecordId before calling refreshRecords.
    if (selectedRecord.value && selectedRecordId.value === wanted) {
      return;
    }
    if (records.value[0] && !selectedRecordId.value) {
      selectRecord(records.value[0]);
      return;
    }
    if (!editingText.value && !metadataEditorDirty.value && !selectedRecordId.value) {
      selectedRecord.value = null;
      sourceBlocks.value = [];
    }
  } catch (exc) {
    reviewHydrated.value = true;
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    if (requestId === recordRequestSerial) recordsLoading.value = false;
  }
}

async function refreshBlocks() {
  if (!selectedAssetId.value || !selectedRecord.value?.source_block_ids?.length) {
    sourceBlocks.value = [];
    return;
  }
  const result = await corpusBuilderApi.blocks(
    selectedAssetId.value,
    0,
    Math.min(1000, selectedRecord.value.source_block_ids.length),
    selectedRecord.value.source_block_ids,
  );
  sourceBlocks.value = result.items;
}
async function ensureReviewHydrated(preferredId = "") {
  if (!selectedBuildId.value || !currentBuild.value || awaitingManifestReview.value) return;
  const expected = Number(
    currentBuild.value.record_count || currentBuild.value.metadata_total || 0,
  );
  if (expected < 1) return;
  await nextTick();
  await refreshRecords(true, preferredId);
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
function selectRecord(record: CorpusRecord) {
  const viewport = captureReviewViewport();
  const sameRecord = selectedRecordId.value === record.record_id;
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
  void loadAdjudicationSuggestions(record);
  const fallback = JSON.stringify(recordMetadata(record), null, 2);
  try {
    metadataDraft.value =
      localStorage.getItem(metadataDraftKey(selectedBuildId.value, record.record_id)) || fallback;
  } catch {
    metadataDraft.value = fallback;
  }

  async function loadAdjudicationSuggestions(record: CorpusRecord) {
    const fields = (currentBuild.value?.schema?.fields || []).map((field) => field.name);
    const results = await Promise.all(
      fields.map(async (field) => {
        try {
          return [
            field,
            await corpusBuilderApi.metadataCache(
              currentBuild.value?.build_id || "",
              record.record_id,
              field,
            ),
          ] as const;
        } catch {
          return null;
        }
      }),
    );
    for (const item of results) {
      if (!item) continue;
      const values = item?.[1]?.suggestions?.prior_values;
      if (!Array.isArray(values)) continue;
      for (const value of values) {
        if (typeof value === "string" && value.trim()) rememberMetadataValues(item[0], value);
      }
    }
  }
  void refreshBlocks();
  if (selectedBuildId.value && !sameRecord)
    void corpusBuilderApi
      .markViewed(selectedBuildId.value, record.record_id)
      .then((result) => {
        if (selectedRecord.value?.record_id === record.record_id)
          selectedRecord.value.activity = result.activity;
      })
      .catch(() => undefined);
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
  for (const record of records.value) {
    if (checked) next.add(record.record_id);
    else next.delete(record.record_id);
  }
  selectedReviewIds.value = next;
}
const allVisibleSelected = computed(
  () =>
    records.value.length > 0 &&
    records.value.every((record) => selectedReviewIds.value.has(record.record_id)),
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
  reviewHydrated.value = false;
  hydratedTopologyCount.value = 0;
  hydratedMetadataCount.value = 0;
  reviewQueue.value = "all";
  await refreshBuild();
  await nextTick();
  await refreshRecords(true);
  if (buildRunning.value) startPolling();
}
async function openPdfExplorer() {
  await router.replace({ query: { ...route.query, mode: "explorer" } });
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

function startNewBuildSetup() {
  stopPolling();
  selectedBuildId.value = "";
  currentBuild.value = null;
  records.value = [];
  recordTotal.value = 0;
  selectedRecordId.value = "";
  selectedRecord.value = null;
  sourceBlocks.value = [];
  reviewHydrated.value = false;
  bulkMetadataOpen.value = false;
  void router.replace({
    query: { ...route.query, build: undefined, record: undefined, queue: undefined },
  });
}
function reviewShortcut(event: KeyboardEvent) {
  if (!selectedRecord.value || busy.value) return;
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
  else if (command === "focus") focusView.value = !focusView.value;
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
watch([reviewQueue, recordQuery], () => {
  selectedRecordId.value = "";
  selectedRecord.value = null;
  metadataEditorDirty.value = false;
  editingText.value = false;
  void refreshRecords(true);
});
watch(selectedEvidenceField, (field) => {
  if (!field || !selectedRecord.value) return;
  const ids = selectedRecord.value.metadata_evidence?.[field]?.block_ids || [];
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
    const enriched = Number(metadataEnriched || 0);
    if (enriched > hydratedMetadataCount.value) {
      hydratedMetadataCount.value = enriched;
      await ensureReviewHydrated(selectedRecordId.value);
    }
    if (!buildId || expected < 1) return;
    const visibleStage =
      ["enriching", "review", "ready"].includes(String(stage || "")) ||
      ["awaiting_review", "ready"].includes(String(status || ""));
    if (!visibleStage) return;
    if (!reviewHydrated.value || expected > hydratedTopologyCount.value) {
      await ensureReviewHydrated(selectedRecordId.value);
    }
  },
  { flush: "post" },
);
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
  [selectedBuildId, reviewQueue, selectedRecordId],
  () => {
    if (!selectedBuildId.value) return;
    const query = {
      ...route.query,
      build: selectedBuildId.value,
      queue: reviewQueue.value,
    } as Record<string, string | undefined>;
    if (selectedRecordId.value) query.record = selectedRecordId.value;
    else delete query.record;
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
  records,
  error,
});
</script>

<template>
  <section class="corpus-builder" :aria-labelledby="'pdf-corpus-builder-title'">
    <CorpusBuilderWorkspaceHeader
      :source-filename="selectedAsset?.filename || ''"
      :build-id="currentBuild?.build_id || ''"
      :publication-id="currentBuild?.publication?.publication_id || ''"
      :stage="currentBuild?.stage || ''"
      :status="currentBuild?.status || ''"
      :record-count="currentBuild?.record_count || 0"
      :accepted-count="currentBuild?.accepted_count || 0"
      :sticky="!showReviewWorkspace"
    >
      <template #actions>
        <CorpusBuildHistoryMenu
          :builds="builds"
          :total="buildsTotal"
          :selected-build-id="selectedBuildId"
          @select="chooseBuild"
          @refresh="refreshBuilds"
        />
        <button
          v-if="
            currentBuild &&
            (buildRunning
              ? canStartConcurrentBuild
              : ['cancelled', 'failed', 'interrupted', 'ready', 'awaiting_review'].includes(
                  String(currentBuild.status || ''),
                ))
          "
          type="button"
          class="btn"
          @click="startNewBuildSetup"
          :disabled="busy !== ''"
        >
          {{
            buildRunning
              ? i18n.t("pdf_corpus.start_concurrent_build")
              : i18n.t("pdf_corpus.start_new_build")
          }}
        </button>
      </template>
    </CorpusBuilderWorkspaceHeader>

    <div
      ref="statusRegion"
      tabindex="-1"
      class="status-region"
      aria-live="polite"
      aria-atomic="true"
    >
      <div
        v-if="error"
        class="builder-message"
        :class="transientNetworkError ? 'warning' : 'error'"
        :role="transientNetworkError ? 'status' : 'alert'"
      >
        <span>{{ displayError }}</span
        ><button
          type="button"
          class="message-dismiss"
          :aria-label="i18n.t('ui.dismiss')"
          @click="error = ''"
        >
          ×
        </button>
      </div>
      <div v-else-if="notice" class="builder-message" role="status">{{ notice }}</div>
    </div>

    <CorpusWorkflowStepper
      :stage="currentBuild?.stage || ''"
      :status="currentBuild?.status || ''"
      :published="Boolean(currentBuild?.publication)"
      :has-asset="Boolean(selectedAsset)"
      :has-manifest="Boolean(currentBuild?.manifest && Object.keys(currentBuild.manifest).length)"
      :accepted-count="currentBuild?.accepted_count || 0"
      :record-count="currentBuild?.record_count || 0"
      :blocker-count="currentBuild?.publication_readiness?.blockers?.length || 0"
      :can-publish="Boolean(currentBuild?.publication_readiness?.can_publish)"
    />
    <CorpusModelActivity
      v-if="currentBuild && buildRunning"
      :activity="currentBuild.llm_activity"
    />
    <CorpusInitializationDialog
      v-if="currentBuild && buildRunning && !hasRecordTopology"
      :build="currentBuild"
      :disabled="busy !== ''"
      @cancel="cancelBuild"
    />

    <section
      v-if="showBuildConfiguration"
      class="builder-setup"
      :aria-labelledby="'pdf-corpus-config-title'"
    >
      <h2 id="pdf-corpus-config-title" class="sr-only">
        {{ i18n.t("pdf_corpus.build_configuration") }}
      </h2>
      <CorpusConfigurationNav
        v-model="configurationSection"
        :has-source="Boolean(selectedAsset)"
        :structure-available="Boolean(selectedAsset)"
      />

      <section
        v-show="configurationSection === 'source'"
        id="corpus-config-panel-source"
        class="setup-section setup-source-section"
        role="tabpanel"
        aria-labelledby="corpus-config-tab-source"
      >
        <div class="setup-section-head">
          <div>
            <div>
              <h3 id="pdf-corpus-source-title">
                {{ i18n.t("pdf_corpus.source_setup_title") }}
              </h3>
              <p>
                {{ i18n.t("pdf_corpus.source_setup_help") }}
              </p>
            </div>
          </div>
        </div>
        <CorpusSourceIngest
          v-model:asset-id="selectedAssetId"
          v-model:illegibility="sourceIllegibility"
          v-model:source-url="sourceUrl"
          v-model:gutenberg-query="gutenbergQuery"
          :assets="assets"
          :hits="gutenbergHits"
          :wikisource-hits="wikisourceHits"
          :gutenberg-status="gutenbergStatus"
          :selected-asset="selectedAsset"
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
        />
        <div v-if="selectedAsset && paginatedSource" class="source-facts">
          <span>{{ selectedAsset.page_count }} {{ i18n.t("pdf_corpus.pages") }}</span
          ><span>{{ selectedAsset.block_count }} {{ i18n.t("pdf_corpus.source_units") }}</span
          ><span>{{ selectedAsset.ocr_pages }} {{ i18n.t("pdf_corpus.ocr_pages") }}</span
          ><span v-if="selectedAsset.metadata?.author"
            ><b>{{ i18n.t("pdf_corpus.pdf_author") }}</b
            >: {{ String(selectedAsset.metadata.author) }}</span
          ><span>SHA-256 {{ selectedAsset.sha256.slice(0, 16) }}…</span
          ><span>{{ formatDate(selectedAsset.created_at) }}</span>
        </div>
        <p v-if="selectedAsset && paginatedSource" class="source-facts-help">
          {{ i18n.t("pdf_corpus.source_facts_help") }}
        </p>
      </section>

      <section
        v-if="paginatedSource && selectedAsset?.pages?.length"
        v-show="configurationSection === 'structure'"
        id="corpus-config-panel-structure"
        class="setup-phase"
        role="tabpanel"
        aria-labelledby="corpus-config-tab-structure"
      >
        <div class="phase-label">
          <div>
            <h3 id="pdf-corpus-structure-phase-title">
              {{ i18n.t("pdf_corpus.document_structure") }}
            </h3>
            <p>
              {{ i18n.t("pdf_corpus.structure_before_build_help") }}
            </p>
          </div>
        </div>
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
      </section>
      <section
        v-else-if="selectedAsset"
        v-show="configurationSection === 'structure'"
        id="corpus-config-panel-structure"
        class="setup-phase"
        role="tabpanel"
        aria-labelledby="corpus-config-tab-structure"
      >
        <div class="phase-label">
          <div>
            <h3 id="media-structure-phase-title">
              {{ i18n.t("pdf_corpus.source_interpretation", "Source interpretation") }}
            </h3>
          </div>
        </div>
        <MediaStructureConfigurator
          :media-kind="selectedAsset.media_kind"
          :filename="selectedAsset.filename"
          :page-count="selectedAsset.page_count"
          :block-count="selectedAsset.block_count"
        />
      </section>

      <CorpusEnrichmentConfiguration
        v-show="configurationSection === 'enrichment'"
        :selected-provider-id="selectedProviderId"
        :selected-review-provider-id="selectedReviewProviderId"
        :provider-profiles="providerProfiles"
        :default-profile-id="runtime.getDefaultProviderProfileId?.() || ''"
        :selected-provider-label="selectedProviderLabel"
        :selected-profile-model="selectedProfileModel"
        :enrichment-mode="enrichmentMode"
        :semantic-indexing="semanticIndexing"
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

      <details v-show="configurationSection === 'structure'" class="setup-section setup-disclosure">
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
          <CorpusRecordSizingSettings v-model="recordSizing" :disabled="busy !== ''" />
        </div>
      </details>
      <CorpusMetadataConfiguration
        v-show="configurationSection === 'metadata'"
        v-model:schema-id="schemaId"
        v-model:run-guidance="runGuidance"
        :schema-choices="schemaChoices"
        :chosen-schema="chosenSchema"
        :run-guidance-fields="runGuidanceFields"
        :disabled="busy !== ''"
        @manage-schemas="schemaEditorOpen = true"
      />

      <CorpusAdvancedConfiguration
        v-show="configurationSection === 'advanced'"
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

      <CorpusBuildReadiness
        :media-kind="selectedAsset?.media_kind"
        :source-filename="selectedAsset?.filename || ''"
        :page-count="selectedAsset?.page_count || 0"
        :block-count="selectedAsset?.block_count || 0"
        :structure-summary="selectedStructureSummary"
        :provider-label="selectedProviderLabel"
        :model-label="selectedProfileModel || manualModel"
        :enrichment-mode="enrichmentMode"
        :target-chars="recordSizing.preferred_record_chars"
        :tolerance-chars="recordSizing.record_length_tolerance"
        :context-safe="contextSafe"
        :active-build-count="activeBuildCount"
        :can-start="canStartConcurrentBuild"
        :busy="busy === 'build'"
        :warnings="setupWarnings"
        @build="startBuild"
      />
    </section>
    <details v-if="currentBuild && !showBuildConfiguration" class="active-build-settings">
      <summary>{{ i18n.t("pdf_corpus.build_settings_summary") }}</summary>
      <div>
        <span>{{ currentBuild.source_filename }}</span
        ><span>{{ i18n.t("pdf_corpus.provider_profile") }}: {{ activeProviderProfileLabel }}</span
        ><span>{{ i18n.t("pdf_corpus.model") }}: {{ activeModelLabel }}</span>
        <details v-if="activeRunGuidance.length" class="active-guidance-summary">
          <summary>
            {{ i18n.t("pdf_corpus.run_guidance_title") }}
          </summary>
          <ul>
            <li v-for="item in activeRunGuidance" :key="item.field">
              <b>{{ item.label }}</b>
              <span v-if="item.instructions">{{ item.instructions }}</span>
              <small v-if="item.lookFor.length">{{ item.lookFor.join(" · ") }}</small>
            </li>
          </ul>
        </details>
        <button
          type="button"
          class="btn small"
          @click="
            selectedBuildId = '';
            currentBuild = null;
          "
        >
          {{
            i18n.t(
              activeBuildCount
                ? "pdf_corpus.configure_another_build"
                : "pdf_corpus.configure_new_build",
              activeBuildCount ? "Configure another build" : "Configure a new build",
            )
          }}
        </button>
      </div>
    </details>

    <div
      v-if="currentBuild || !showBuildConfiguration"
      class="builder-workspace"
      :class="{ 'review-mode': showReviewWorkspace }"
    >
      <aside
        v-if="!showReviewWorkspace"
        class="build-rail"
        :aria-label="i18n.t('pdf_corpus.builds')"
      >
        <div class="rail-title">
          <div>
            <b>{{ i18n.t("pdf_corpus.builds") }}</b
            ><span>{{ buildsTotal }} {{ i18n.t("pdf_corpus.total") }}</span>
          </div>
          <button
            type="button"
            class="icon-button"
            :title="i18n.t('pdf_corpus.refresh_builds')"
            :aria-label="i18n.t('pdf_corpus.refresh_builds')"
            @click="refreshBuilds"
          >
            ↻
          </button>
        </div>
        <button
          v-for="build in builds"
          :key="build.build_id"
          type="button"
          class="build-row"
          :class="{ active: build.build_id === selectedBuildId }"
          :aria-current="build.build_id === selectedBuildId ? 'true' : undefined"
          @click="chooseBuild(build)"
        >
          <span class="status-dot" :data-status="build.status" aria-hidden="true"></span>
          <span
            ><b>{{ build.source_filename }}</b
            ><small>{{ statusLabel(build) }} · {{ Math.round((build.progress || 0) * 100) }}%</small
            ><small
              >{{ build.record_count || 0 }} {{ i18n.t("pdf_corpus.records") }} ·
              {{ formatDate(build.created_at) }}</small
            ></span
          >
        </button>
        <div v-if="!builds.length" class="rail-empty">
          {{ i18n.t("pdf_corpus.no_builds") }}
        </div>
      </aside>

      <main class="build-main">
        <section
          v-if="currentBuild"
          class="build-summary"
          :aria-labelledby="'pdf-corpus-current-build'"
        >
          <div v-if="!showReviewWorkspace" class="summary-top">
            <div>
              <span class="eyebrow">{{ currentBuild.profile_id }}</span>
              <h2 id="pdf-corpus-current-build">{{ currentBuild.source_filename }}</h2>
              <p>{{ currentBuild.build_id }}</p>
            </div>
            <div class="summary-actions">
              <button v-if="buildRunning" type="button" class="btn" @click="cancelBuild">
                {{ i18n.t("pdf_corpus.cancel") }}
              </button>
              <button
                v-if="canResume"
                type="button"
                class="btn"
                @click="resumeBuild"
                :disabled="busy !== ''"
              >
                {{ i18n.t("pdf_corpus.resume") }}
              </button>
              <a
                v-if="currentBuild.publication"
                class="btn primary"
                :href="corpusBuilderApi.publicationUrl(currentBuild.publication.publication_id)"
                >{{ i18n.t("pdf_corpus.download_jsonl") }}</a
              >
            </div>
          </div>
          <CorpusBuildLifecycleCard v-if="!showReviewWorkspace" :build="currentBuild" />
          <CorpusQualitySummary
            v-if="!awaitingManifestReview && !showReviewWorkspace"
            :build="currentBuild"
          />

          <CorpusBuildStageNotice
            v-if="buildRunning && !hasRecordTopology"
            :stage="currentBuild.stage"
          />
          <CorpusFinishWorkspace
            v-if="!awaitingManifestReview && finishPhase && !showReviewWorkspace"
            :build="currentBuild"
            :busy="busy !== ''"
            @retry-metadata="retryIncompleteMetadata"
            @review-metadata="openMetadataIssueQueue"
            @review-validation="openValidationIssueQueue"
            @review-topology="openTopologyIssueQueue"
            @review-issues="openIssueQueue"
            @review-rejected="openRejectedQueue"
            @review-records="openAllReviewQueue"
            @review-source="openSourceIssueQueue"
            @restore-rejected="restoreAllRejected"
            @start-new="startNewBuildSetup"
            @edit-document-metadata="documentMetadataOpen = true"
            @rerun-enrichment="openEnrichmentFromFinish"
            @publish="publish({ download: false })"
          />
          <CorpusMetadataIssues
            v-if="
              !awaitingManifestReview &&
              finishPhase &&
              metadataFieldIssueCount > 0 &&
              !currentBuild.publication
            "
            :build="currentBuild"
            :busy="busy !== '' || metadataRetryRunning"
            @retry="retryIncompleteMetadata"
            @review="reviewMetadataRecord"
          />
          <CorpusBuildTimeline
            v-if="!awaitingManifestReview && !showReviewWorkspace"
            :build="currentBuild"
          />
          <details v-if="!showReviewWorkspace" class="technical-details">
            <summary>
              {{ i18n.t("pdf_corpus.technical_details") }}
            </summary>
            <CorpusBuildProgress
              :status="currentBuild.publication ? 'published' : currentBuild.status"
              :stage="currentBuild.publication ? 'published' : currentBuild.stage"
              :progress="currentBuild.progress || 0"
              :record-count="currentBuild.record_count || 0"
              :review-count="currentBuild.needs_review_count || 0"
              :accepted-count="currentBuild.accepted_count || 0"
              :error="currentBuild.error"
              :warnings="currentBuild.warnings || []"
              :validation="currentBuild.validation || null"
              :llm-metrics="currentBuild.llm_metrics || null"
              :metadata-operation="currentBuild.metadata_operation || null"
              :unresolved-count="
                currentBuild.boundary_review_count ||
                currentBuild.segmentation_unresolved_regions?.length ||
                0
              "
              :segmentation-telemetry="{
                candidateCount: currentBuild.boundary_candidate_count || 0,
                deterministicSplits: currentBuild.boundary_deterministic_split_count || 0,
                deterministicKeeps: currentBuild.boundary_deterministic_keep_count || 0,
                llmAdjudications: currentBuild.boundary_llm_adjudication_count || 0,
                llmBatchCalls: currentBuild.boundary_llm_batch_call_count || 0,
                llmSplits: currentBuild.boundary_llm_split_count || 0,
                llmKeeps: currentBuild.boundary_llm_keep_count || 0,
                provisionalSplits: currentBuild.provisional_boundary_count || 0,
                sizeOptimizedSplits: currentBuild.size_optimized_boundary_count || 0,
                absoluteSafetySplits: currentBuild.absolute_safety_boundary_count || 0,
                budgetSkipped: currentBuild.boundary_budget_skipped_count || 0,
                classifierFailures: currentBuild.boundary_classifier_failure_count || 0,
                reviewCount: currentBuild.boundary_review_count || 0,
              }"
            />
          </details>
          <section
            v-if="awaitingManifestReview"
            class="manifest-gate"
            aria-labelledby="manifest-review-title"
          >
            <div>
              <h3 id="manifest-review-title">
                {{ i18n.t("pdf_corpus.manifest_review_required") }}
              </h3>
              <p>
                {{ i18n.t("pdf_corpus.manifest_review_required_help") }}
              </p>
            </div>
            <button
              type="button"
              class="btn primary"
              @click="confirmManifest"
              :disabled="busy !== '' || !contextSafe"
            >
              {{ i18n.t("pdf_corpus.confirm_manifest_continue") }}
            </button>
          </section>
          <section
            v-if="retryingSegmentation"
            class="build-guidance running-guidance"
            role="status"
            aria-live="polite"
          >
            <span class="guidance-icon" aria-hidden="true">↻</span>
            <div>
              <h3>
                {{ i18n.t("pdf_corpus.retry_in_progress") }}
              </h3>
              <p>
                {{ i18n.t("pdf_corpus.retry_in_progress_help") }}
              </p>
            </div>
          </section>
          <section
            v-else-if="
              currentBuild.status === 'failed' ||
              currentBuild.status === 'interrupted' ||
              currentBuild.status === 'cancelled'
            "
            class="build-guidance failure-guidance"
            role="alert"
          >
            <span class="guidance-icon" aria-hidden="true">!</span>
            <div>
              <h3>
                {{ i18n.t("pdf_corpus.build_stopped_title") }}
              </h3>
              <p>
                {{ currentBuild.error || i18n.t("pdf_corpus.build_stopped_help") }}
              </p>
              <small>{{ i18n.t("pdf_corpus.build_stopped_checkpoint") }}</small>
            </div>
          </section>
          <section
            v-if="segmentationNeedsReview && !showReviewWorkspace"
            class="segmentation-blocked segmentation-review-localized"
            role="status"
            aria-labelledby="segmentation-review-title"
          >
            <div>
              <h3 id="segmentation-review-title">
                {{ i18n.t("pdf_corpus.segmentation_review_title") }}
              </h3>
              <p>
                {{ i18n.t("pdf_corpus.segmentation_review_help") }}
              </p>
            </div>
            <details v-if="currentBuild.segmentation_unresolved_regions?.length">
              <summary>
                {{
                  i18n.tf("pdf_corpus.unresolved_count", {
                    count: currentBuild.segmentation_unresolved_regions.length,
                  })
                }}
              </summary>
              <ul>
                <li
                  v-for="(region, index) in currentBuild.segmentation_unresolved_regions.slice(
                    0,
                    20,
                  )"
                  :key="index"
                >
                  <code>{{
                    region.after_block_id || region.left_block_id || region.start_block_id || "?"
                  }}</code>
                  →
                  <code>{{
                    region.next_block_id || region.right_block_id || region.end_block_id || "?"
                  }}</code
                  ><span v-if="region.reason"> · {{ region.reason }}</span>
                </li>
              </ul>
            </details>
          </section>
          <details
            v-if="
              currentBuild.manifest &&
              Object.keys(currentBuild.manifest).length &&
              !showReviewWorkspace
            "
            class="manifest-details"
            :open="awaitingManifestReview"
          >
            <summary>
              {{ i18n.t("pdf_corpus.document_manifest") }} ·
              {{ i18n.t("pdf_corpus.revision") }}
              {{ currentBuild.manifest_revision || 1 }}
            </summary>
            <DocumentManifestEditor
              :media-kind="selectedAsset?.media_kind"
              :manifest="currentBuild.manifest || {}"
              :disabled="buildRunning || busy !== ''"
              @save="saveManifest"
              @reanalyze="reanalyzeDocument"
            />
          </details>
          <div v-if="!showReviewWorkspace" class="provenance-strip">
            <span>SHA {{ currentBuild.source_sha256?.slice(0, 12) }}…</span
            ><span>{{
              currentBuild.model || selectedProfileModel || i18n.t("pdf_corpus.provider_default")
            }}</span
            ><span
              >{{ i18n.t("schemas.version") }} v{{
                currentBuild.metadata_schema_version || "—"
              }}</span
            ><span>{{ currentBuild.segmentation_prompt_version }}</span>
          </div>
        </section>

        <template v-if="showReviewWorkspace">
          <CorpusRunMonitor
            v-if="currentBuild"
            :build="currentBuild"
            :profiles="providerProfiles"
            :active-profile-id="activeBuildProfileId"
            :active-model="activeModelLabel"
            :disabled="busy !== ''"
            @switch-profile="switchBuildProvider"
            @settle="settleMetadata"
            @cancel="cancelBuild"
            @run-another="
              llmActionProviderId =
                llmActionProviderId || selectedProviderId || providerProfiles[0]?.id || '';
              metadataEnrichmentOpen = true;
            "
            @open-record="openHandsFreeException"
            @inspect-editorial-memory="openEditorialMemory"
          />

          <CorpusReviewSessionBar
            v-if="currentBuild"
            :source-filename="currentBuild.source_filename"
            :model="currentBuild.model"
            :build-id="currentBuild.build_id"
            :accepted="Number(currentBuild.accepted_count || 0)"
            :reviewable="readyCount"
            :remaining="pendingCount"
            :issues="issueCount"
            :focus-disabled="!selectedRecord"
            @focus="openFocusView"
          />

          <div ref="reviewFrameEl" class="review-frame">
            <section class="review-toolbar" :aria-label="i18n.t('pdf_corpus.review_controls')">
              <CorpusReviewQueueTabs
                v-if="currentBuild"
                v-model="reviewQueue"
                :total="currentBuild.record_count || 0"
                :ready="readyCount"
                :issues="issueCount"
                :metadata="Number(reviewQueueCounts.metadata ?? metadataIssueCount)"
                :topology="topologyIssueCount"
                :source-problems="
                  Number(reviewQueueCounts.source ?? currentBuild.source_problem_count ?? 0)
                "
                :accepted="Number(reviewQueueCounts.accepted ?? currentBuild.accepted_count ?? 0)"
                :rejected="Number(reviewQueueCounts.rejected ?? currentBuild.rejected_count ?? 0)"
                :disabled="busy !== ''"
              />
              <label class="sr-only" for="pdf-corpus-record-search">{{
                i18n.t("pdf_corpus.search_records")
              }}</label
              ><input
                id="pdf-corpus-record-search"
                v-model="recordQuery"
                class="control"
                :placeholder="i18n.t('pdf_corpus.search_records')"
              />
              <div
                class="workspace-switcher"
                role="group"
                :aria-label="i18n.t('pdf_corpus.review_workspace')"
              >
                <button
                  type="button"
                  class="btn small"
                  :aria-pressed="reviewWorkspaceMode === 'record'"
                  @click="setReviewWorkspaceMode('record')"
                >
                  {{ i18n.t("pdf_corpus.workspace.record") }}</button
                ><button
                  type="button"
                  class="btn small"
                  :aria-pressed="reviewWorkspaceMode === 'metadata'"
                  :aria-label="i18n.t('pdf_corpus.workspace.metadata')"
                  :disabled="!selectedRecord"
                  @click="setReviewWorkspaceMode('metadata')"
                >
                  {{ i18n.t("pdf_corpus.workspace.metadata_short") }}</button
                ><button
                  type="button"
                  class="btn small"
                  :aria-pressed="reviewWorkspaceMode === 'source'"
                  :aria-label="i18n.t('pdf_corpus.workspace.source')"
                  :disabled="!selectedRecord"
                  @click="setReviewWorkspaceMode('source')"
                >
                  {{ i18n.t("pdf_corpus.workspace.source_short") }}
                </button>
              </div>
              <div class="review-bulk">
                <button
                  type="button"
                  class="btn small primary"
                  @click="acceptCleanRecords"
                  :disabled="busy !== '' || readyCount === 0"
                >
                  {{
                    i18n.tf("pdf_corpus.accept_clean", {
                      count: readyCount,
                    })
                  }}</button
                ><CorpusActionMenu
                  :label="i18n.t('pdf_corpus.bulk_actions')"
                  :items="bulkActionItems"
                  :disabled="busy !== ''"
                  placement="bottom"
                  @select="runBulkAction"
                />
              </div>
              <p
                v-if="bulkActionFeedback"
                class="review-action-feedback"
                role="status"
                aria-live="polite"
              >
                {{ bulkActionFeedback }}
              </p>
              <CorpusBulkMetadataEditor
                v-if="bulkMetadataOpen"
                :schema="currentBuild?.schema"
                :records="records"
                :known-values="metadataKnownValues"
                :region-types="regionTypes"
                :discourse-roles="discourseRoles"
                :selected-count="selectedReviewCount"
                :total-count="Number(currentBuild?.record_count || recordTotal)"
                :disabled="busy !== '' || reviewLocked"
                @apply="applyBulkMetadata"
                @close="bulkMetadataOpen = false"
              />
              <div class="pager">
                <button
                  type="button"
                  class="btn small"
                  @click="previousPage"
                  :disabled="recordOffset === 0"
                >
                  {{ i18n.t("ui.previous") }}</button
                ><span>{{ pageNumber }} / {{ pageCount }}</span
                ><button
                  type="button"
                  class="btn small"
                  @click="nextPage"
                  :disabled="recordOffset + pageSize >= recordTotal"
                >
                  {{ i18n.t("ui.next") }}
                </button>
              </div>
            </section>

            <section
              ref="reviewGridEl"
              class="review-grid record-first-review"
              :style="{
                '--rw-queue': `${queueSplitter.size.value}px`,
                '--rw-inspector': `${inspectorSplitter.size.value}px`,
                height: `${reviewHeightSplitter.size.value}px`,
              }"
              :class="{
                'queue-collapsed': reviewQueueCollapsed,
                'detail-mode': reviewWorkspaceMode !== 'record',
                'metadata-workspace': reviewWorkspaceMode === 'metadata',
                'source-workspace': reviewWorkspaceMode === 'source',
              }"
              :aria-busy="recordsLoading"
            >
              <CorpusReviewRecordQueue
                :records="records"
                :record-total="recordTotal"
                :selected-record-id="selectedRecordId"
                :selected-review-ids="selectedReviewIds"
                :all-visible-selected="allVisibleSelected"
                :loading="recordsLoading"
                :hydrated="reviewHydrated"
                :disabled="busy !== ''"
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
              />
              <div
                v-if="!reviewQueueCollapsed"
                class="review-splitter"
                data-splitter="queue"
                role="separator"
                tabindex="0"
                aria-orientation="vertical"
                :aria-label="i18n.t('pdf_corpus.resize_queue')"
                v-bind="queueSplitter.aria()"
                @pointerdown="queueSplitter.onPointerDown"
                @keydown="queueSplitter.onKeydown"
                @dblclick="queueSplitter.reset"
              ></div>

              <article
                v-show="reviewWorkspaceMode === 'record'"
                ref="reviewPaneEl"
                class="record-review-pane"
                :aria-labelledby="selectedRecord ? 'review-record-title' : undefined"
              >
                <template v-if="selectedRecord">
                  <header class="record-review-head">
                    <div>
                      <button
                        v-if="reviewQueueCollapsed"
                        type="button"
                        class="link-button queue-toggle"
                        @click="reviewQueueCollapsed = false"
                      >
                        {{ i18n.t("pdf_corpus.show_queue") }}</button
                      ><span class="eyebrow">{{ i18n.t("pdf_corpus.proposed_record") }}</span>
                      <h3 id="review-record-title">{{ selectedRecord.record_id }}</h3>
                      <p>
                        {{ selectedRecord.inline_citation }}
                        · {{ selectedRecord.text_length.toLocaleString() }}
                        {{ i18n.t("pdf_corpus.characters") }}{{ selectedRecordActivitySummary }}
                      </p>
                    </div>
                    <div class="record-head-actions">
                      <div
                        class="decision-history"
                        role="group"
                        :aria-label="i18n.t('pdf_corpus.record_history')"
                      >
                        <button
                          type="button"
                          class="btn small"
                          @click="undoReview"
                          :disabled="busy !== ''"
                        >
                          <AppIcon name="history" /><span class="btn-text">{{
                            i18n.t("pdf_corpus.undo")
                          }}</span></button
                        ><button
                          type="button"
                          class="btn small"
                          @click="redoReview"
                          :disabled="busy !== ''"
                        >
                          <AppIcon name="history" class="flip-inline" /><span class="btn-text">{{
                            i18n.t("pdf_corpus.redo")
                          }}</span>
                        </button>
                      </div>
                      <button type="button" class="btn small" @click="openFocusView">
                        {{ i18n.t("pdf_corpus.focus_view") }}
                      </button>
                    </div>
                  </header>
                  <aside
                    v-if="selectedRecord.text_touchup_proposal?.status === 'pending_review'"
                    class="review-reason touchup-review-notice"
                    role="status"
                  >
                    <b>{{ i18n.t("pdf_corpus.llm_touchup_proposal_available") }}</b
                    ><span>{{ i18n.t("pdf_corpus.llm_touchup_proposal_help") }}</span
                    ><button
                      type="button"
                      class="btn small"
                      @click="beginTextEdit(true)"
                      :disabled="busy !== '' || reviewLocked"
                    >
                      {{ i18n.t("pdf_corpus.review_touchup_proposal") }}
                    </button>
                  </aside>
                  <aside
                    v-else-if="
                      selectedRecord.review_reason &&
                      selectedRecord.review_reason.toLowerCase() !== 'pending human review.'
                    "
                    class="review-reason"
                    role="note"
                  >
                    <b>{{
                      recordIssueKinds(selectedRecord).length
                        ? recordIssueKinds(selectedRecord)
                            .map((kind) => i18n.t(`pdf_corpus.record_state.${kind}`, kind))
                            .join(" · ")
                        : i18n.t("pdf_corpus.why_review")
                    }}</b
                    ><span>{{ selectedRecord.review_reason }}</span>
                  </aside>
                  <section class="record-text-review" aria-labelledby="reviewed-record-text-title">
                    <header>
                      <div>
                        <b id="reviewed-record-text-title">{{
                          i18n.t("pdf_corpus.reviewed_record_text")
                        }}</b
                        ><span
                          v-if="selectedRecord.text_review_status === 'human_corrected'"
                          class="human-corrected"
                          >{{ i18n.t("pdf_corpus.human_corrected") }}</span
                        ><span
                          v-else-if="selectedRecord.text_review_status === 'human_reviewed'"
                          class="human-corrected"
                          >{{ i18n.t("pdf_corpus.human_reviewed") }}</span
                        >
                      </div>
                      <div class="record-text-head-actions">
                        <button
                          v-if="editingText"
                          type="button"
                          class="btn small"
                          @click="textCleanupOpen = true"
                          :disabled="busy !== '' || reviewLocked"
                        >
                          {{ i18n.t("pdf_corpus.clean_text") }}</button
                        ><button
                          v-if="editingText"
                          type="button"
                          class="btn small"
                          @click="llmTouchupOpen = true"
                          :disabled="busy !== '' || reviewLocked"
                        >
                          {{ i18n.t("pdf_corpus.llm_touchup") }}</button
                        ><button
                          v-if="
                            !editingText &&
                            selectedRecord.text_review_status !== 'human_corrected' &&
                            selectedRecord.text_review_status !== 'human_reviewed'
                          "
                          type="button"
                          class="btn small"
                          @click="markTextReviewed"
                          :disabled="busy !== '' || reviewLocked"
                        >
                          {{ i18n.t("pdf_corpus.mark_text_reviewed") }}</button
                        ><button
                          type="button"
                          class="btn small"
                          @click="editingText ? cancelTextEdit() : beginTextEdit()"
                          :disabled="busy !== '' || reviewLocked"
                        >
                          {{ editingText ? i18n.t("ui.cancel") : i18n.t("pdf_corpus.edit_text") }}
                        </button>
                      </div>
                    </header>
                    <textarea
                      v-if="editingText"
                      v-model="textDraft"
                      class="record-text-editor"
                      :aria-label="i18n.t('pdf_corpus.reviewed_record_text')"
                    ></textarea>
                    <div v-else class="record-primary-text">{{ selectedRecord.text }}</div>
                    <p
                      v-if="selectedRecord.text_noise?.score != null"
                      class="record-noise-summary"
                      role="status"
                    >
                      {{
                        i18n.tf("pdf_corpus.text_noise.score", {
                          score: Math.round(Number(selectedRecord.text_noise.score)),
                        })
                      }}
                      <span v-if="selectedRecord.text_noise.unusable">
                        ·
                        {{ i18n.t("pdf_corpus.text_noise.unusable") }}
                      </span>
                    </p>
                    <div
                      v-if="editingText && selectedRecord.source_quality_issues?.length"
                      class="text-review-actions"
                    >
                      <label
                        v-if="selectedRecord.source_quality_issues?.length"
                        class="resolve-source-check"
                        ><input v-model="resolveSourceOnTextSave" type="checkbox" /><span>{{
                          i18n.t("pdf_corpus.resolve_source_with_correction")
                        }}</span></label
                      >
                    </div>
                  </section>
                  <footer class="record-decision-dock">
                    <p
                      v-if="selectedMetadataBlocked"
                      id="record-metadata-blocker"
                      class="metadata-accept-blocker"
                      role="status"
                    >
                      <b>{{ i18n.t("pdf_corpus.metadata_decision_required") }}</b>
                      {{
                        i18n.tf("pdf_corpus.resolve_metadata_before_accept_fields", {
                          fields: selectedMetadataBlockingLabel,
                        })
                      }}
                    </p>
                    <div
                      v-if="editingText"
                      class="decision-bar text-edit-bar"
                      role="group"
                      :aria-label="i18n.t('pdf_corpus.edit_text')"
                    >
                      <span class="text-save-hint">{{ i18n.t("pdf_corpus.text_save_hint") }}</span>
                      <div class="decision-actions">
                        <button type="button" class="btn small" @click="cancelTextEdit">
                          {{ i18n.t("ui.cancel") }}
                        </button>
                        <button
                          type="button"
                          class="btn small primary"
                          @click="saveReviewedText()"
                          :disabled="busy !== '' || !textDraft.trim()"
                        >
                          {{
                            busy === "text"
                              ? i18n.t("ui.saving")
                              : i18n.t("pdf_corpus.save_and_mark_reviewed")
                          }}
                        </button>
                      </div>
                    </div>
                    <div
                      v-else
                      class="decision-bar"
                      role="group"
                      :aria-label="i18n.t('pdf_corpus.record_decision')"
                    >
                      <CorpusActionMenu
                        :label="i18n.t('pdf_corpus.more_actions')"
                        :menu-label="i18n.t('pdf_corpus.more_record_actions')"
                        :items="recordActionItems"
                        :disabled="busy !== ''"
                        placement="top"
                        @select="runRecordAction"
                      />
                      <div class="decision-actions">
                        <button
                          type="button"
                          class="btn small"
                          @click="skipRecord"
                          :disabled="busy !== ''"
                        >
                          {{ i18n.t("pdf_corpus.skip") }}
                        </button>
                        <button
                          type="button"
                          class="btn small danger"
                          @click="rejectRecord"
                          :disabled="busy !== ''"
                        >
                          {{ i18n.t("pdf_corpus.reject_next") }}
                        </button>
                        <button
                          ref="acceptButtonEl"
                          type="button"
                          class="btn small primary"
                          @click="toggleAccept"
                          :disabled="busy !== '' || reviewLocked"
                          :aria-describedby="
                            selectedMetadataBlocked ? 'record-metadata-blocker' : undefined
                          "
                        >
                          {{
                            selectedRecord.accepted
                              ? i18n.t("pdf_corpus.reopen")
                              : i18n.t("pdf_corpus.accept_next")
                          }}
                        </button>
                      </div>
                    </div>
                  </footer>
                </template>
                <div v-else class="inspector-empty">
                  {{ i18n.t("pdf_corpus.select_record") }}
                </div>
              </article>

              <div
                v-if="reviewWorkspaceMode === 'record'"
                class="review-splitter"
                data-splitter="inspector"
                role="separator"
                tabindex="0"
                aria-orientation="vertical"
                :aria-label="i18n.t('pdf_corpus.resize_inspector')"
                v-bind="inspectorSplitter.aria()"
                @pointerdown="inspectorSplitter.onPointerDown"
                @keydown="inspectorSplitter.onKeydown"
                @dblclick="inspectorSplitter.reset"
              ></div>
              <aside
                ref="reviewInspectorEl"
                class="review-inspector"
                :aria-label="i18n.t('pdf_corpus.review_details')"
              >
                <div v-if="reviewWorkspaceMode !== 'record'" class="detail-workspace-head">
                  <div>
                    <span class="eyebrow">{{ i18n.t("pdf_corpus.review_workspace") }}</span>
                    <h3>
                      {{
                        reviewWorkspaceMode === "metadata"
                          ? i18n.t("pdf_corpus.workspace.metadata")
                          : i18n.t("pdf_corpus.workspace.source")
                      }}
                    </h3>
                    <p>
                      {{
                        reviewWorkspaceMode === "metadata"
                          ? i18n.t("pdf_corpus.workspace.metadata_help")
                          : i18n.t("pdf_corpus.workspace.source_help")
                      }}
                    </p>
                  </div>
                  <button type="button" class="btn small" @click="setReviewWorkspaceMode('record')">
                    {{ i18n.t("pdf_corpus.workspace.back_record") }}
                  </button>
                </div>
                <div
                  v-show="reviewWorkspaceMode === 'record'"
                  class="review-inspector-tabs"
                  role="tablist"
                  :aria-label="i18n.t('pdf_corpus.review_detail_views')"
                >
                  <button
                    id="review-tab-metadata"
                    data-review-tab="metadata"
                    type="button"
                    role="tab"
                    aria-controls="review-panel-metadata"
                    :aria-selected="reviewInspectorTab === 'metadata'"
                    :tabindex="reviewInspectorTab === 'metadata' ? 0 : -1"
                    @keydown="reviewInspectorKeydown"
                    @click="reviewInspectorTab = 'metadata'"
                  >
                    {{ i18n.t("pdf_corpus.metadata_tab")
                    }}<span v-if="selectedMetadataBlockingFields.length">{{
                      selectedMetadataBlockingFields.length
                    }}</span>
                  </button>
                  <button
                    id="review-tab-evidence"
                    data-review-tab="evidence"
                    type="button"
                    role="tab"
                    aria-controls="review-panel-evidence"
                    :aria-selected="reviewInspectorTab === 'evidence'"
                    :tabindex="reviewInspectorTab === 'evidence' ? 0 : -1"
                    @keydown="reviewInspectorKeydown"
                    @click="reviewInspectorTab = 'evidence'"
                  >
                    {{ i18n.t("pdf_corpus.evidence_tab") }}
                  </button>
                  <button
                    id="review-tab-source"
                    data-review-tab="source"
                    type="button"
                    role="tab"
                    aria-controls="review-panel-source"
                    :aria-selected="reviewInspectorTab === 'source'"
                    :tabindex="reviewInspectorTab === 'source' ? 0 : -1"
                    @keydown="reviewInspectorKeydown"
                    @click="reviewInspectorTab = 'source'"
                  >
                    {{ i18n.t("pdf_corpus.source_tab") }}
                  </button>
                </div>
                <section
                  v-if="
                    selectedRecord &&
                    (reviewWorkspaceMode === 'metadata' ||
                      (reviewWorkspaceMode === 'record' && reviewInspectorTab === 'metadata'))
                  "
                  id="review-panel-metadata"
                  class="review-inspector-panel"
                  role="tabpanel"
                  aria-labelledby="review-tab-metadata"
                  tabindex="0"
                >
                  <CorpusMetadataResolutionPanel
                    :schema="currentBuild?.schema"
                    :record="selectedRecord"
                    :region-types="regionTypes"
                    :discourse-roles="discourseRoles"
                    :busy="busy !== '' && busy !== 'metadata-field'"
                    :batch-saving="metadataSavingField === '__batch__'"
                    :saving-field="metadataSavingField"
                    :saved-field="metadataSavedField"
                    :confidence-calibration="currentBuild?.llm_confidence_calibration || {}"
                    :known-values="metadataKnownValues"
                    @resolve="resolveMetadataField"
                    @no-value="resolveMetadataNoValue"
                    @resolve-many="resolveMetadataSuggestions"
                    @source="showMetadataSource"
                    @selection-evidence="assignSelectedMetadataEvidence"
                    @dirty="handleMetadataDirty"
                  />
                  <button
                    type="button"
                    class="btn small metadata-cache-clear"
                    :disabled="busy !== ''"
                    @click="clearMetadataSuggestionCache"
                  >
                    {{ i18n.t("pdf_corpus.clear_metadata_cache") }}
                  </button>
                  <section v-if="currentBuild?.manifest" class="document-metadata-launch">
                    <div>
                      <b>{{ i18n.t("pdf_corpus.document_metadata_defaults") }}</b
                      ><span>{{ i18n.t("pdf_corpus.document_metadata_defaults_help") }}</span>
                    </div>
                    <button
                      type="button"
                      class="btn"
                      :disabled="busy !== ''"
                      @click="documentMetadataOpen = true"
                    >
                      {{ i18n.t("pdf_corpus.edit_document_metadata") }}
                    </button>
                  </section>
                  <details class="record-data">
                    <summary>
                      {{ i18n.t("pdf_corpus.advanced_metadata") }}
                    </summary>
                    <p class="help">
                      {{ i18n.t("pdf_corpus.metadata_help") }}
                    </p>
                    <LlmExecutionControl
                      :model-value="llmActionProviderId || selectedProviderId"
                      :model-override="llmActionModel"
                      :profiles="providerProfiles"
                      :disabled="busy !== ''"
                      :task="i18n.t('pdf_corpus.metadata_rerun_provider_help')"
                      @update:model-value="(value) => (llmActionProviderId = value)"
                      @update:model-override="(value) => (llmActionModel = value)"
                    /><label class="sr-only" for="pdf-corpus-metadata">{{
                      i18n.t("pdf_corpus.interpretive_metadata")
                    }}</label
                    ><textarea
                      id="pdf-corpus-metadata"
                      v-model="metadataDraft"
                      class="metadata-json"
                      spellcheck="false"
                      @input="metadataEditorDirty = true"
                    ></textarea>
                    <div class="data-actions">
                      <button
                        type="button"
                        class="btn small"
                        @click="saveMetadata"
                        :disabled="busy !== ''"
                      >
                        {{ i18n.t("pdf_corpus.save_metadata") }}</button
                      ><label class="rerun-family"
                        ><span>{{ i18n.t("pdf_corpus.rerun_family") }}</span
                        ><select v-model="metadataRerunFamily" class="control small">
                          <option value="all">
                            {{ i18n.t("pdf_corpus.metadata_family.all") }}
                          </option>
                          <option
                            v-for="family in metadataFamilyOptions"
                            :key="family.key"
                            :value="family.key"
                          >
                            {{ family.label }}
                          </option>
                        </select></label
                      ><button
                        type="button"
                        class="btn small"
                        :title="i18n.t('pdf_corpus.rerun_metadata_help')"
                        @click="rerunMetadata()"
                        :disabled="busy !== ''"
                      >
                        {{ i18n.t("pdf_corpus.rerun_metadata") }}</button
                      ><button
                        type="button"
                        class="btn small soft"
                        :title="i18n.t('pdf_corpus.requeue_metadata_help')"
                        @click="requeueCurrentRecord"
                        :disabled="busy !== ''"
                      >
                        {{ i18n.t("pdf_corpus.requeue_metadata") }}</button
                      ><button
                        type="button"
                        class="btn small"
                        :title="i18n.t('pdf_corpus.metadata_enrichment_again_help')"
                        @click="
                          llmActionProviderId =
                            llmActionProviderId ||
                            selectedProviderId ||
                            providerProfiles[0]?.id ||
                            '';
                          metadataEnrichmentOpen = true;
                        "
                        :disabled="busy !== ''"
                      >
                        {{ i18n.t("pdf_corpus.metadata_enrichment_again") }}
                      </button>
                    </div>
                  </details>
                </section>
                <section
                  v-else-if="
                    selectedRecord &&
                    reviewWorkspaceMode === 'record' &&
                    reviewInspectorTab === 'evidence'
                  "
                  id="review-panel-evidence"
                  class="review-inspector-panel"
                  role="tabpanel"
                  aria-labelledby="review-tab-evidence"
                  tabindex="0"
                >
                  <p class="inspector-help">
                    {{ i18n.t("pdf_corpus.evidence_review_help") }}
                  </p>
                  <FieldEvidenceList
                    :evidence="selectedRecord.metadata_evidence || {}"
                    :fields="evidenceCandidateFields"
                    :selected-field="selectedEvidenceField"
                    @select="selectedEvidenceField = $event"
                  />
                  <div v-if="selectedEvidenceField" class="source-blocks compact-source-blocks">
                    <article
                      v-for="block in visibleBlocks"
                      :key="block.block_id"
                      class="source-block"
                      :class="{ 'evidence-block': evidenceBlockIds.has(block.block_id) }"
                    >
                      <header>
                        <span>{{ block.block_id }}</span
                        ><span
                          >{{
                            block.locator_kind === "time"
                              ? timeLabel(block.start, block.end)
                              : paginatedSource
                                ? block.page
                                : block.block_id
                          }}
                          · {{ block.speaker || block.type }}</span
                        >
                      </header>
                      <p>{{ block.text }}</p>
                      <button
                        type="button"
                        class="evidence-toggle"
                        :aria-pressed="evidenceBlockIds.has(block.block_id)"
                        @click="toggleEvidenceBlock(block.block_id)"
                        :disabled="busy !== ''"
                      >
                        {{
                          evidenceBlockIds.has(block.block_id)
                            ? i18n.t("pdf_corpus.remove_evidence")
                            : i18n.t("pdf_corpus.add_evidence")
                        }}
                        · {{ selectedEvidenceField }}
                      </button>
                    </article>
                  </div>
                </section>
                <section
                  v-else-if="
                    selectedRecord &&
                    (reviewWorkspaceMode === 'record' || reviewWorkspaceMode === 'source')
                  "
                  id="review-panel-source"
                  class="review-inspector-panel source-review-panel"
                  role="tabpanel"
                  aria-labelledby="review-tab-source"
                  tabindex="0"
                >
                  <CorpusSourceSummary
                    :media-kind="selectedAsset?.media_kind"
                    :audio-url="audioSourceUrl"
                    :image-url="imageSourceUrl"
                    :show-pdf-explorer="selectedSourceCapabilities.pdfViewer"
                    :pdf-url="sourcePdfUrl"
                    :page="selectedPdfPage"
                    :page-count="selectedAsset?.page_count || 0"
                    :page-width="selectedPageMeta?.width || 0"
                    :page-height="selectedPageMeta?.height || 0"
                    :blocks="selectedPageBlocks"
                    :evidence-block-ids="evidenceIdsArray"
                    :zoomable="reviewWorkspaceMode === 'source'"
                    :can-previous="selectedPdfPageIndex > 0"
                    :can-next="selectedPdfPageIndex < recordPdfPages.length - 1"
                    @previous="previousSourcePage"
                    @next="nextSourcePage"
                    @open-viewer="sourceTranscriptionOpen = true"
                    @open-pdf-explorer="openPdfExplorer"
                  />
                  <details class="source-tool-section">
                    <summary>
                      {{ i18n.t("pdf_corpus.boundary_second_reader") }}
                    </summary>
                    <CorpusBoundaryAdjudication
                      :record="selectedRecord"
                      :can-previous="canMergePrevious"
                      :can-next="canMergeNext"
                      :busy="busy !== ''"
                      :profiles="providerProfiles"
                      :provider-profile-id="llmActionProviderId || selectedProviderId"
                      :model-override="llmActionModel"
                      :concurrency-risk="
                        Boolean(
                          providerProfiles.find(
                            (p) => p.id === (llmActionProviderId || selectedProviderId),
                          )?.type === 'ollama' &&
                            llmActionConcurrentLoad + 1 >
                              Number(
                                providerProfiles.find(
                                  (p) => p.id === (llmActionProviderId || selectedProviderId),
                                )?.max_concurrent_requests || 1,
                              ),
                        )
                      "
                      :active-requests="llmActionConcurrentLoad"
                      :concurrency-limit="
                        Number(
                          providerProfiles.find(
                            (p) => p.id === (llmActionProviderId || selectedProviderId),
                          )?.max_concurrent_requests || 1,
                        )
                      "
                      @update:provider-profile-id="(value) => (llmActionProviderId = value)"
                      @update:model-override="(value) => (llmActionModel = value)"
                      @adjudicate="adjudicateBoundary"
                    />
                  </details>
                  <details class="source-tool-section">
                    <summary>
                      {{ i18n.t("pdf_corpus.extracted_source_text") }}
                    </summary>
                    <p class="inspector-help">
                      {{ i18n.t("pdf_corpus.extracted_source_text_help") }}
                    </p>
                    <pre
                      v-if="selectedRecord.source_extracted_text"
                      class="original-extraction-snapshot"
                      >{{ selectedRecord.source_extracted_text }}</pre
                    >
                    <div class="source-blocks">
                      <article
                        v-for="(block, index) in visibleBlocks"
                        :key="block.block_id"
                        class="source-block"
                        :class="{ 'evidence-block': evidenceBlockIds.has(block.block_id) }"
                      >
                        <header>
                          <span>{{ block.block_id }}</span
                          ><span
                            >{{
                              block.locator_kind === "time"
                                ? timeLabel(block.start, block.end)
                                : paginatedSource
                                  ? block.page
                                  : block.block_id
                            }}
                            · {{ block.speaker || block.type }}</span
                          >
                        </header>
                        <p>{{ block.text }}</p>
                        <button
                          v-if="selectedEvidenceField"
                          type="button"
                          class="evidence-toggle"
                          :aria-pressed="evidenceBlockIds.has(block.block_id)"
                          @click="toggleEvidenceBlock(block.block_id)"
                          :disabled="busy !== ''"
                        >
                          {{
                            evidenceBlockIds.has(block.block_id)
                              ? i18n.t("pdf_corpus.remove_evidence")
                              : i18n.t("pdf_corpus.add_evidence")
                          }}
                          · {{ selectedEvidenceField }}</button
                        ><button
                          v-if="index < visibleBlocks.length - 1"
                          type="button"
                          class="split-button"
                          @click="split(block.block_id)"
                          :disabled="busy !== ''"
                        >
                          {{ i18n.t("pdf_corpus.split_after") }}
                        </button>
                      </article>
                    </div>
                  </details>
                  <details class="source-tool-section">
                    <summary>
                      {{ i18n.t("pdf_corpus.revision_history") }}
                    </summary>
                    <CorpusRevisionHistory :record="selectedRecord" />
                  </details>
                </section>
                <div v-else class="inspector-empty">
                  {{ i18n.t("pdf_corpus.select_record") }}
                </div>
              </aside>
            </section>
            <div
              class="review-height-splitter"
              data-splitter="review-height"
              role="separator"
              tabindex="0"
              aria-orientation="horizontal"
              :aria-label="i18n.t('pdf_corpus.resize_review_height')"
              v-bind="reviewHeightSplitter.aria()"
              @pointerdown="reviewHeightSplitter.onPointerDown"
              @keydown="reviewHeightSplitter.onKeydown"
              @dblclick="reviewHeightSplitter.reset"
            ></div>
          </div>
        </template>

        <section v-else class="builder-empty">
          <h2>{{ i18n.t("pdf_corpus.no_selected_build") }}</h2>
          <p>
            {{ i18n.t("pdf_corpus.no_selected_build_help") }}
          </p>
        </section>
      </main>
    </div>

    <DocumentManifestDialog
      v-if="documentMetadataOpen && currentBuild?.manifest"
      @reanalyze="reanalyzeDocument"
      :manifest="currentBuild.manifest || {}"
      :disabled="busy !== ''"
      :affected-records="Number(currentBuild.record_count || 0)"
      @save="saveManifest"
      @close="documentMetadataOpen = false"
    />

    <Teleport to="body"
      ><CorpusBoundarySliceDialog
        v-if="boundarySliceOpen && selectedRecord"
        :text="String(selectedRecord.text || '')"
        :can-previous="canMergePrevious"
        :can-next="canMergeNext"
        :busy="busy !== ''"
        @close="boundarySliceOpen = false"
        @slice="sliceRecord"
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
        <button type="button" class="btn small" @click="openSchemasPage">
          {{ i18n.t("schemas.open_page", "Open as a page") }}
        </button>
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
        ><button type="button" class="btn" @click="handsFreeOpen = false">
          {{ i18n.t("ui.cancel") }}</button
        ><button type="button" class="btn primary" :disabled="busy !== ''" @click="runHandsFree">
          {{ i18n.t("pdf_corpus.run_hands_free_action") }}
        </button></template
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
    <Teleport to="body"
      ><CorpusRecordFocusReview
        v-if="focusView && selectedRecord"
        :record="selectedRecord"
        :schema="currentBuild?.schema"
        :source-blocks="visibleBlocks"
        :busy="busy !== '' || reviewLocked"
        :can-merge-previous="canMergePrevious"
        :can-merge-next="canMergeNext"
        :can-accept="!selectedMetadataBlocked"
        :region-types="regionTypes"
        :discourse-roles="discourseRoles"
        :confidence-calibration="currentBuild?.llm_confidence_calibration || {}"
        :source-pdf-url="
          selectedAsset
            ? `${corpusBuilderApi.assetContentUrl(selectedAsset.asset_id)}#page=${selectedPdfPage || 1}`
            : ''
        "
        :source-pdf-page="selectedPdfPage"
        :source-pdf-page-count="selectedAsset?.page_count || 0"
        :source-page-width="selectedPageMeta?.width || 0"
        :source-page-height="selectedPageMeta?.height || 0"
        :can-history-back="focusHistoryIndex > 0"
        :can-history-forward="focusHistoryIndex >= 0 && focusHistoryIndex < focusHistory.length - 1"
        :can-previous-record="selectedRecordIndex > 0 || recordOffset > 0"
        :can-next-record="
          selectedRecordIndex >= 0 &&
          (selectedRecordIndex < records.length - 1 || recordOffset + pageSize < recordTotal)
        "
        :provider-profiles="providerProfiles"
        :llm-provider-profile-id="llmActionProviderId || selectedProviderId"
        :llm-model-override="llmActionModel"
        :editing-text="editingText"
        :text-draft="textDraft"
        :resolve-source-issues="resolveSourceOnTextSave"
        @close="focusView = false"
        @history-back="focusHistoryMove(-1)"
        @history-forward="focusHistoryMove(1)"
        @previous-record="focusQueueMove(-1)"
        @next-record="focusQueueMove(1)"
        @requeue-metadata="requeueCurrentRecord"
        @request-slice="boundarySliceOpen = true"
        @open-source-issue="recordSourceWarningOpen = true"
        @begin-text-edit="beginTextEdit"
        @cancel-text-edit="cancelTextEdit"
        @save-text="saveReviewedText"
        @text-draft-change="textDraft = $event"
        @resolve-source-issues-change="resolveSourceOnTextSave = $event"
        @open-text-cleanup="textCleanupOpen = true"
        @resolve-metadata="resolveMetadataField"
        @resolve-metadata-many="resolveMetadataSuggestions"
        @confirm-no-metadata-value="resolveMetadataNoValue"
        @metadata-dirty="handleMetadataDirty"
        @preview-jsonl="openJsonlPreview"
        @llm-touchup="openLlmTouchup"
        @accept="acceptFromFocus"
        @reject="setDisposition('rejected')"
        @skip="skipRecord"
        @undo="undoReview"
        @redo="redoReview"
        @slice="sliceRecord"
        @merge="merge"
        @update-llm-provider-profile="(value) => (llmActionProviderId = value)"
        @update-llm-model="(value) => (llmActionModel = value)"
        @adjudicate-boundary="adjudicateBoundary"
        @open-source-viewer="sourceTranscriptionOpen = true"
        :just-processed-record-id="justProcessedRecordId"
        :next-record-id="nextQueueRecordId"
        :selected-evidence-field="selectedEvidenceField"
        :evidence-block-ids="[...evidenceBlockIds]"
        @select-evidence="selectedEvidenceField = $event"
        @toggle-evidence="toggleEvidenceBlock"
        @assign-evidence="assignEvidenceBlock"
        @navigate-record="navigateToQueueRecord"
    /></Teleport>
  </section>
</template>

<style scoped src="../features/corpus-builder/CorpusBuilderWorkspace.css"></style>
