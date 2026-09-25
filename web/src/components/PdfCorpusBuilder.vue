<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  pdfCorpusApi,
  type CorpusBuild,
  type CorpusRecord,
  type SourceBlock,
  type AutonomousPolicy,
} from "../api/pdfCorpus";
import { systemApi, type ProviderProfile } from "../api/system";
import { useI18nStore } from "../stores/i18n";
import ProviderProfileSelect from "./ProviderProfileSelect.vue";
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
import CorpusExecutionSettings from "./CorpusExecutionSettings.vue";
import CorpusWorkflowStepper from "./CorpusWorkflowStepper.vue";
import CorpusBuildReadiness from "./CorpusBuildReadiness.vue";
import CorpusSourceIngest from "./CorpusSourceIngest.vue";
import CorpusBuildHistoryMenu from "./CorpusBuildHistoryMenu.vue";
import CorpusQualitySummary from "./CorpusQualitySummary.vue";
import CorpusRecordSizingSettings from "./CorpusRecordSizingSettings.vue";
import CorpusRunGuidance from "./CorpusRunGuidance.vue";
import CorpusRecordFocusReview from "./CorpusRecordFocusReview.vue";
import CorpusReviewQueueTabs from "./CorpusReviewQueueTabs.vue";
import type { RecordSizingPolicy, ReviewQueue } from "../types/corpus";
import CorpusBuildLifecycleCard from "./CorpusBuildLifecycleCard.vue";
import CorpusMetadataIssues from "./CorpusMetadataIssues.vue";
import CorpusBuildTimeline from "./CorpusBuildTimeline.vue";
import CorpusFinishWorkspace from "./CorpusFinishWorkspace.vue";
import CorpusMetadataResolutionPanel from "./CorpusMetadataResolutionPanel.vue";
import CorpusBuildStageNotice from "./CorpusBuildStageNotice.vue";
import CorpusMetadataLiveStatus from "./CorpusMetadataLiveStatus.vue";
import CorpusSourceQualityDialog from "./CorpusSourceQualityDialog.vue";
import CorpusBulkMetadataEditor from "./CorpusBulkMetadataEditor.vue";
import CorpusTextCleanupDialog from "./CorpusTextCleanupDialog.vue";
import CorpusProviderSwitcher from "./CorpusProviderSwitcher.vue";
import CorpusLlmEffectivenessPanel from "./CorpusLlmEffectivenessPanel.vue";
import CorpusEditorialMemoryDialog from "./CorpusEditorialMemoryDialog.vue";
import CorpusReviewSessionBar from "./CorpusReviewSessionBar.vue";
import CorpusTextCleanupSummary from "./CorpusTextCleanupSummary.vue";
import CorpusRevisionHistory from "./CorpusRevisionHistory.vue";
import CorpusJsonlPreviewDialog from "./CorpusJsonlPreviewDialog.vue";
import CorpusLlmTextTouchupDialog from "./CorpusLlmTextTouchupDialog.vue";
import CorpusBoundarySliceDialog from "./CorpusBoundarySliceDialog.vue";
import CorpusBoundaryAdjudication from "./CorpusBoundaryAdjudication.vue";
import MetadataEnrichmentDialog from "./MetadataEnrichmentDialog.vue";
import CorpusEnrichmentPassStatus from "./CorpusEnrichmentPassStatus.vue";
import CorpusEnrichmentMetrics from "./CorpusEnrichmentMetrics.vue";
import CorpusModelActivity from "./CorpusModelActivity.vue";
import CorpusHandsFreeSettings from "./CorpusHandsFreeSettings.vue";
import CorpusTextNoiseSettings from "./CorpusTextNoiseSettings.vue";
import MetadataSchemaEditor from "./MetadataSchemaEditor.vue";
import {
  metadataSchemasApi,
  type MetadataSchema,
  type SchemaSummary,
} from "../api/metadataSchemas";
import CorpusHandsFreeReport from "./CorpusHandsFreeReport.vue";
import UiDialog from "./ui/UiDialog.vue";
import LlmExecutionControl from "./LlmExecutionControl.vue";
import { useCorpusBuildLifecycle } from "../composables/useCorpusBuildLifecycle";
import { usePdfCorpusPaneSizing } from "../composables/usePdfCorpusPaneSizing";
import { useCorpusIngestWarning } from "../composables/useCorpusIngestWarning";
import { useCorpusRunGuidance } from "../composables/useCorpusRunGuidance";
import { useCorpusReviewWorkspace } from "../features/corpus-builder/composables/useCorpusReviewWorkspace";
import { useCorpusSourceConfiguration } from "../features/corpus-builder/composables/useCorpusSourceConfiguration";
import { corpusReviewCommandFromKeydown } from "../features/corpus-builder/domain/reviewCommands";
import { editableRecordMetadata } from "../features/corpus-builder/domain/recordMetadata";
import AppIcon from "./AppIcon.vue";
import CorpusActionMenu, { type CorpusActionMenuItem } from "./CorpusActionMenu.vue";
import { recordState, recordIssueKinds } from "../domain/corpusReview";
import { RecordMutationQueue } from "../domain/recordMutationQueue";
import {
  firstRecordWithSourceWarning,
  hideSourceWarnings,
  recordHasSourceWarning,
  sourceWarningsHidden,
} from "../domain/sourceQuality";
import { recurringShortLines } from "../domain/textCleanup";
import * as runtime from "../runtime/runtime.js";

const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const builds = ref<CorpusBuild[]>([]);
const buildsTotal = ref(0);
const providerProfiles = ref<ProviderProfile[]>([]);
const corpusProfiles = ref<Array<Record<string, unknown>>>([]);
const serverProviderIds = ref<Set<string>>(new Set());
const selectedProviderId = ref("");
const selectedReviewProviderId = ref("");
const recordSourceWarningOpen = ref(false);
const sourceProblemDialogBuildId = ref("");
const selectedBuildId = ref("");
const currentBuild = ref<CorpusBuild | null>(null);
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
    currentBuild.value = await pdfCorpusApi.runAutonomous(currentBuild.value.build_id, {
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
  lastIngestedAsset,
  refreshAssets,
  upload,
  loadSourceUrl,
  searchGutenberg,
  importGutenberg,
  savePageLabels,
  saveDocumentLayout,
} = useCorpusSourceConfiguration(busy, setMessage);
const metadataSavingField = ref("");
const metadataSavedField = ref("");
const error = ref("");
const notice = ref("");
const statusRegion = ref<HTMLElement | null>(null);
const acceptButtonEl = ref<HTMLButtonElement | null>(null);
const manualProvider = ref<"ollama" | "openai">("ollama");
const manualModel = ref("");
const manualBaseUrl = ref("");
const manualApiKey = ref("");
const advancedOpen = ref(false);
const useProfileDefaults = ref(true);
const generationOverrides = ref<Record<string, unknown>>({});
const maxConcurrentRequests = ref(1);
const stageLimits = ref<Record<string, number>>({
  manifest_num_predict: 1800,
  segmentation_num_predict: 1200,
  reconciliation_num_predict: 1000,
  discourse_num_predict: 1600,
  quotation_num_predict: 1500,
  indexing_num_predict: 1200,
  segmentation_window_tokens: 5000,
});
const stageTimeouts = ref<Record<string, number>>({
  manifest: 300,
  segmentation: 300,
  reconciliation: 240,
  discourse: 240,
  quotation: 240,
  indexing: 180,
});
const recordSizing = ref<RecordSizingPolicy>({
  preferred_record_chars: 1750,
  record_length_tolerance: 200,
  long_record_chars: 3500,
  absolute_record_chars: 6000,
});
const metadataDraft = ref("{}");
const recordSaveQueue = new RecordMutationQueue();
const textDraft = ref("");
const editingText = ref(false);
const bulkMetadataOpen = ref(false);
const documentMetadataOpen = ref(false);
const textCleanupOpen = ref(false);
const jsonlPreviewOpen = ref(false);
const jsonlPreview = ref<{
  jsonl: string;
  validation_errors: string[];
  unresolved_fields: string[];
  would_publish: boolean;
}>({ jsonl: "", validation_errors: [], unresolved_fields: [], would_publish: false });
const llmTouchupOpen = ref(false);
const boundarySliceOpen = ref(false);
const sourceTranscriptionOpen = ref(false);
const metadataEnrichmentOpen = ref(false);
const llmActionProviderId = ref("");
const llmActionModel = ref("");
const llmTouchupResult = ref<{
  source_text: string;
  proposed_text: string;
  changes: string[];
  warnings: string[];
  provider: string;
  model: string;
  proposal_id?: string;
  run_id?: string;
  created_at?: string;
  status?: string;
  no_change: boolean;
}>({
  source_text: "",
  proposed_text: "",
  changes: [],
  warnings: [],
  provider: "",
  model: "",
  no_change: false,
});
const llmTouchupError = ref("");
const metadataEditorDirty = ref(false);
const editorialMemoryOpen = ref(false);
const editorialMemory = ref<{
  conventions: Record<string, { value: unknown; confirmed_records: number }>;
  examples: Record<
    string,
    Array<{ record_id: string; value: unknown; similarity: number; excerpt: string }>
  >;
  reset_at?: string | null;
  convention_count: number;
  example_count: number;
}>({ conventions: {}, examples: {}, convention_count: 0, example_count: 0 });
const bulkActionFeedback = ref("");
const resolveSourceOnTextSave = ref(false);
const enrichmentMode = ref<"fast" | "deep">("fast");
const semanticIndexing = ref(true);
const autoCleanText = ref(true);
const llmTouchupDuringEnrichment = ref(false);
const noiseUnusableThreshold = ref(45);
const llmAssessTextNoise = ref(false);
const metadataRerunFamily = ref("all");
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
let pollTimer: number | undefined;
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
function recordStateLabel(record: CorpusRecord) {
  const state = recordState(record);
  return i18n.t(
    `pdf_corpus.record_state.${state}`,
    state === "ready" ? "Ready" : state.replace(/_/g, " "),
  );
}
// A shape as well as a colour, so a record's state never depends on colour alone (WCAG 1.4.1).
function recordStateIcon(record: CorpusRecord) {
  const state = recordState(record);
  return state === "accepted"
    ? "check"
    : state === "rejected"
      ? "close"
      : state === "metadata" || state === "topology" || state === "source"
        ? "warning"
        : state === "preparing"
          ? "refresh"
          : "";
}
// The status already says the primary state; list only the other issues, so a row never says "Metadata" twice.
function extraIssueKinds(record: CorpusRecord) {
  const state = recordState(record);
  return recordIssueKinds(record).filter((kind: string) => kind !== state);
}
function recordLlmProcessed(record: CorpusRecord) {
  if (record.metadata_enrichment_finished) return true;
  if (String(record.metadata_enrichment_state || "") === "complete") return true;
  return Object.values(record.metadata_stage_status || {}).some((value) =>
    ["complete", "needs_review"].includes(String(value || "")),
  );
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
  const candidates = [
    "speaker",
    "position_holder",
    "target",
    "stance",
    "proposition_status",
    "quoted_speaker",
    "quoted_author",
    "quoted_work",
    "quoted_position_holder",
    "quoted_addressee",
    "quoted_referent",
    "quotation_chain",
  ];
  return candidates.filter((field) => {
    const value = record[field];
    return Array.isArray(value)
      ? value.length > 0
      : value !== null && value !== undefined && value !== "";
  });
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
const nextQueueRecordId = computed(() => {
  const index = selectedRecordIndex.value;
  return index >= 0 ? records.value[index + 1]?.record_id || "" : "";
});
const canMergePrevious = computed(() => {
  const topo = Number(selectedRecord.value?.topology_index ?? -1);
  return topo >= 0 ? topo > 0 : recordOffset.value + Math.max(0, selectedRecordIndex.value) > 0;
});
const canMergeNext = computed(() => {
  const index = Number(selectedRecord.value?.topology_index ?? -1),
    total = Number(selectedRecord.value?.topology_count ?? recordTotal.value);
  if (index >= 0 && total > 0) return index < total - 1;
  const globalIndex = recordOffset.value + selectedRecordIndex.value;
  return globalIndex >= 0 && globalIndex < recordTotal.value - 1;
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
function mergeUnavailable(direction: "previous" | "next"): string | undefined {
  if (busy.value !== "") return i18n.t("pdf_corpus.reason.busy");
  if (structuralReviewLocked.value) return i18n.t("pdf_corpus.reason.structure_locked");
  if (direction === "previous" && !canMergePrevious.value)
    return i18n.t("pdf_corpus.reason.no_previous");
  if (direction === "next" && !canMergeNext.value) return i18n.t("pdf_corpus.reason.no_next");
  return undefined;
}
function sliceUnavailable(): string | undefined {
  if (busy.value !== "") return i18n.t("pdf_corpus.reason.busy");
  if (editingText.value) return i18n.t("pdf_corpus.reason.finish_text_edit");
  if (metadataEditorDirty.value) return i18n.t("pdf_corpus.reason.finish_metadata_edit");
  if (!canMergePrevious.value && !canMergeNext.value)
    return i18n.t("pdf_corpus.reason.no_neighbour");
  return undefined;
}
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
const llmContribution = computed(() => currentBuild.value?.llm_contribution || {});
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
    ? pdfCorpusApi.assetContentUrl(selectedAssetId.value)
    : "",
);
const audioSourceUrl = computed(() =>
  selectedSourceCapabilities.value.audioPlayer && selectedAssetId.value
    ? pdfCorpusApi.assetContentUrl(selectedAssetId.value)
    : "",
);
const sourcePdfUrl = computed(() =>
  selectedSourceCapabilities.value.pdfViewer && selectedAssetId.value
    ? pdfCorpusApi.assetContentUrl(selectedAssetId.value)
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
const selectedProfile = computed(
  () => providerProfiles.value.find((profile) => profile.id === selectedProviderId.value) || null,
);
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
const metadataHumanValues = ref<Record<string, Set<string>>>({});
const metadataObservedValues = ref<Record<string, string[]>>({});
const metadataKnownValues = computed<Record<string, string[]>>(() => {
  const out: Record<string, Set<string>> = {};
  for (const [field, values] of Object.entries(metadataObservedValues.value))
    for (const value of values) (out[field] ??= new Set()).add(value);
  for (const row of records.value) {
    for (const [field, value] of Object.entries(row as Record<string, unknown>)) {
      const values = Array.isArray(value) ? value : [value];
      for (const item of values) {
        if (typeof item !== "string" || !item.trim()) continue;
        (out[field] ??= new Set()).add(item.trim());
      }
    }
  }
  for (const [field, values] of Object.entries(metadataHumanValues.value)) {
    for (const value of values) (out[field] ??= new Set()).add(value);
  }
  return Object.fromEntries(
    Object.entries(out).map(([field, values]) => [
      field,
      [...values].sort((a, b) => a.localeCompare(b)),
    ]),
  );
});
const selectedMetadataBlocked = computed(() =>
  Boolean(
    (selectedRecord.value?.metadata_review_fields || []).length ||
      (selectedRecord.value?.metadata_incomplete_fields || []).length,
  ),
);
const selectedMetadataBlockingFields = computed(() =>
  Array.from(
    new Set([
      ...(selectedRecord.value?.metadata_incomplete_fields || []),
      ...(selectedRecord.value?.metadata_review_fields || []),
    ]),
  ),
);
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
const selectedProfileModel = computed(() => String(selectedProfile.value?.model || ""));
const profileGeneration = computed<Record<string, unknown>>(() => {
  if (!selectedProviderId.value) return {};
  const payload = directProfilePayload(selectedProviderId.value);
  const generation = payload?.generation;
  return generation && typeof generation === "object"
    ? { ...(generation as Record<string, unknown>) }
    : {};
});
const effectiveGeneration = computed<Record<string, unknown>>(() =>
  useProfileDefaults.value
    ? profileGeneration.value
    : { ...profileGeneration.value, ...generationOverrides.value },
);
const effectiveNumCtx = computed(() => Number(effectiveGeneration.value.num_ctx || 0));
const requiredContext = computed(
  () =>
    Number(stageLimits.value.segmentation_window_tokens || 5000) +
    Number(stageLimits.value.segmentation_num_predict || 1200) +
    1536,
);
const contextSafe = computed(
  () => !effectiveNumCtx.value || requiredContext.value <= effectiveNumCtx.value,
);
const selectedProviderLabel = computed(
  () =>
    selectedProfile.value?.name ||
    selectedProviderId.value ||
    (manualProvider.value === "openai" ? "OpenAI-compatible" : "Ollama"),
);
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

function directProfilePayload(profileId: string): Record<string, unknown> | null {
  const config = runtime.getProviderRequestConfigForUi?.(profileId, {
    textReview: false,
  }) as Record<string, unknown> | null;
  if (!config) return null;
  const ollama = config.ollama;
  return {
    provider_profile_id: profileId,
    provider: config.provider,
    model: config.model,
    base_url: config.base_url,
    api_key: config.api_key,
    max_concurrent_requests: Math.max(1, Math.min(16, Number(config.max_concurrent_requests || 1))),
    generation:
      config.provider === "ollama" && ollama && typeof ollama === "object" ? ollama : undefined,
  };
}

function directProfilePayloadWithModel(
  profileId: string,
  modelOverride = "",
): Record<string, unknown> | null {
  const payload = directProfilePayload(profileId);
  if (!payload) return null;
  return modelOverride ? { ...payload, model: modelOverride } : payload;
}
const providerPayload = computed<Record<string, unknown>>(() => {
  const buildGeneration = useProfileDefaults.value ? null : { ...effectiveGeneration.value };
  if (selectedProviderId.value) {
    const primary = directProfilePayload(selectedProviderId.value) || {
      provider_profile_id: selectedProviderId.value,
    };
    const payload: Record<string, unknown> = {
      ...primary,
      use_profile_defaults: useProfileDefaults.value,
    };
    if (!useProfileDefaults.value) payload.generation = buildGeneration;
    // A published profile can fill in a missing key. The browser key still has
    // to travel with the request, or a profile without one calls OpenAI
    // unauthenticated.
    if (serverProviderIds.value.has(selectedProviderId.value)) {
      delete payload.provider;
      if (useProfileDefaults.value) delete payload.generation;
    }
    payload.max_concurrent_requests = maxConcurrentRequests.value;
    payload.stage_limits = { ...stageLimits.value };
    payload.stage_timeouts = { ...stageTimeouts.value };
    payload.record_sizing = { ...recordSizing.value };
    payload.enrichment_mode = enrichmentMode.value;
    payload.semantic_indexing = semanticIndexing.value;
    payload.auto_clean_text = autoCleanText.value;
    payload.llm_touchup_during_enrichment = llmTouchupDuringEnrichment.value;
    payload.noise_unusable_threshold = noiseUnusableThreshold.value;
    payload.llm_assess_text_noise = llmAssessTextNoise.value;
    payload.text_cleanup_rules = [
      "page_numbers",
      "repeated_short_lines",
      "line_hyphenation",
      "paragraph_lines",
      "empty_lines",
      "ocr_artifacts",
      "whitespace",
    ];
    if (
      selectedReviewProviderId.value &&
      selectedReviewProviderId.value !== selectedProviderId.value
    ) {
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
    return payload;
  }
  const payload: Record<string, unknown> = {
    provider: manualProvider.value,
    use_profile_defaults: false,
    max_concurrent_requests: maxConcurrentRequests.value,
    stage_limits: { ...stageLimits.value },
    stage_timeouts: { ...stageTimeouts.value },
    record_sizing: { ...recordSizing.value },
    enrichment_mode: enrichmentMode.value,
    semantic_indexing: semanticIndexing.value,
    auto_clean_text: autoCleanText.value,
    llm_touchup_during_enrichment: llmTouchupDuringEnrichment.value,
    noise_unusable_threshold: noiseUnusableThreshold.value,
    llm_assess_text_noise: llmAssessTextNoise.value,
    text_cleanup_rules: [
      "page_numbers",
      "repeated_short_lines",
      "line_hyphenation",
      "paragraph_lines",
      "empty_lines",
      "ocr_artifacts",
      "whitespace",
    ],
  };
  if (manualModel.value.trim()) payload.model = manualModel.value.trim();
  if (manualBaseUrl.value.trim()) payload.base_url = manualBaseUrl.value.trim();
  if (manualApiKey.value) payload.api_key = manualApiKey.value;
  if (Object.keys(generationOverrides.value).length)
    payload.generation = { ...generationOverrides.value };
  return payload;
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
function registerBuildOperation(build: CorpusBuild) {
  const asset = assets.value.find((item) => item.asset_id === build.asset_id);
  const total = Math.max(1, Number(asset?.block_count || 1));
  const progress = Math.max(0, Math.min(1, Number(build.progress || 0)));
  runtime.registerExternalJob?.({
    id: build.build_id,
    build_id: build.build_id,
    type: "pdf_corpus",
    kind: "pdf_corpus",
    label: `${i18n.t("pdf_corpus.corpus_builder")} · ${build.source_filename || ""}`,
    status: ["queued", "running"].includes(build.status)
      ? build.status
      : build.status === "blocked"
        ? "blocked"
        : "completed",
    raw_status: build.status,
    stage: build.stage,
    stage_detail: build.stage,
    source_filename: build.source_filename,
    progress,
    total,
    completed: Math.min(total, Math.round(total * progress)),
    record_count: Number(build.record_count || 0),
    review_count: Number(build.needs_review_count || 0),
    unresolved_regions: Number(build.segmentation_unresolved_regions?.length || 0),
    created_at: build.created_at,
    started_at: build.started_at,
    finished_at: build.finished_at,
  });
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
function applyOptimisticMetadata(changes: Record<string, unknown>) {
  if (!currentBuild.value || !selectedRecord.value) return null;
  const buildId = currentBuild.value.build_id;
  const recordId = selectedRecord.value.record_id;
  const expectedRevision = Number(selectedRecord.value.record_revision || 1);
  const row: CorpusRecord = {
    ...selectedRecord.value,
    ...changes,
    record_revision: expectedRevision + 1,
  } as CorpusRecord;
  // Do not invent canonical authority during an optimistic save. The server
  // response creates the durable human assertion and becomes authoritative.
  selectedRecord.value = row;
  metadataDraft.value = JSON.stringify(recordMetadata(row), null, 2);
  const index = records.value.findIndex((item) => item.record_id === recordId);
  if (index >= 0) records.value.splice(index, 1, row);
  metadataEditorDirty.value = false;
  try {
    localStorage.removeItem(metadataDraftKey(buildId, recordId));
  } catch {
    // Best effort: browser storage must not block review.
  }
  return { buildId, recordId, expectedRevision };
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
    currentBuild.value = await pdfCorpusApi.switchProviderProfile(selectedBuildId.value, payload);
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

async function refreshProviders() {
  const runtimeProfiles = (runtime.getProviderProfilesForUi?.() || []) as ProviderProfile[];
  const defaultId = String(runtime.getDefaultProviderProfileId?.() || "");
  const publishProfiles = (profiles: ProviderProfile[]) => {
    providerProfiles.value = profiles;
    if (
      !selectedProviderId.value ||
      !profiles.some((profile) => profile.id === selectedProviderId.value)
    ) {
      selectedProviderId.value =
        profiles.find((profile) => profile.id === defaultId)?.id || profiles[0]?.id || "";
    }
    if (
      !llmActionProviderId.value ||
      !profiles.some((profile) => profile.id === llmActionProviderId.value)
    ) {
      llmActionProviderId.value = selectedProviderId.value;
    }
  };
  publishProfiles(runtimeProfiles);
  let serverProfiles: ProviderProfile[] = [];
  try {
    serverProfiles = (await systemApi.researcherProviders()).profiles || [];
  } catch {
    serverProfiles = [];
  }
  serverProviderIds.value = new Set(serverProfiles.map((profile) => profile.id));
  const merged = new Map<string, ProviderProfile>();
  // Runtime profiles are the source of truth for administrators; researcher
  // profiles from the server fill in when the native view mounts before legacy
  // runtime bootstrap has completed. Prefer the richer runtime copy on conflicts.
  for (const profile of serverProfiles) merged.set(profile.id, profile);
  for (const profile of runtimeProfiles) merged.set(profile.id, profile);
  const mergedProfiles = Array.from(merged.values());
  // Publish the configured profiles before probing availability. Provider
  // pickers must be usable while network status checks are still running.
  publishProfiles(mergedProfiles);
  const availability = await Promise.all(
    mergedProfiles.map(async (profile) => {
      try {
        if (serverProviderIds.value.has(profile.id)) {
          const status = await systemApi.researcherProviderAvailability(profile.id);
          return {
            ...profile,
            available: Boolean(status.available && status.model_available),
            availability_error:
              status.error ||
              (!status.model_available
                ? `Configured model "${status.configured_model || profile.model || "unknown"}" was not found.`
                : ""),
          };
        }
        const config = directProfilePayload(profile.id);
        if (!config)
          return {
            ...profile,
            available: false,
            availability_error: "Provider configuration is unavailable.",
          };
        const status = await systemApi.llmStatus({
          provider: config.provider,
          base_url: config.base_url,
          api_key: config.api_key,
        });
        const names = new Set((status.models || []).map((model) => String(model.name || "")));
        const modelAvailable = Boolean(config.model && names.has(String(config.model)));
        return {
          ...profile,
          available: Boolean(status.available && modelAvailable),
          availability_error:
            status.error ||
            (!modelAvailable
              ? `Configured model "${String(config.model || "unknown")}" was not found.`
              : ""),
        };
      } catch (exc) {
        return {
          ...profile,
          available: false,
          availability_error: exc instanceof Error ? exc.message : String(exc),
        };
      }
    }),
  );
  providerProfiles.value = availability;
  const activeBuildProfile = String(
    (currentBuild.value?.request as Record<string, unknown> | undefined)?.provider_profile_id || "",
  );
  if (
    activeBuildProfile &&
    providerProfiles.value.some((profile) => profile.id === activeBuildProfile)
  ) {
    selectedProviderId.value = activeBuildProfile;
  } else if (
    !currentBuild.value ||
    !selectedProviderId.value ||
    !providerProfiles.value.some((profile) => profile.id === selectedProviderId.value)
  ) {
    selectedProviderId.value =
      providerProfiles.value.find(
        (profile) => profile.id === defaultId && profile.available !== false,
      )?.id ||
      providerProfiles.value.find((profile) => profile.available !== false)?.id ||
      "";
  }
}
async function refreshCorpusProfiles() {
  try {
    corpusProfiles.value = (await pdfCorpusApi.profiles()).items || [];
  } catch {
    corpusProfiles.value = [];
  }
}
async function refreshBuilds() {
  const result = await pdfCorpusApi.listBuilds(0, 100);
  builds.value = result.items;
  buildsTotal.value = result.total;
  const requested = String(route.query.build || "");
  if (requested && builds.value.some((build) => build.build_id === requested))
    selectedBuildId.value = requested;
  else if (
    (!selectedBuildId.value ||
      !builds.value.some((build) => build.build_id === selectedBuildId.value)) &&
    builds.value[0]
  )
    selectedBuildId.value = builds.value[0].build_id;
  else if (!builds.value.length) {
    selectedBuildId.value = "";
    currentBuild.value = null;
  }
}
function syncBuildInRail(build: CorpusBuild) {
  const index = builds.value.findIndex((item) => item.build_id === build.build_id);
  if (index >= 0) builds.value.splice(index, 1, { ...builds.value[index], ...build });
  else builds.value.unshift(build);
}
async function refreshBuild() {
  if (!selectedBuildId.value) {
    currentBuild.value = null;
    return;
  }
  try {
    currentBuild.value = await pdfCorpusApi.build(selectedBuildId.value);
    syncBuildInRail(currentBuild.value);
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    return;
  }
  if (currentBuild.value?.asset_id) selectedAssetId.value = currentBuild.value.asset_id;
  const request = currentBuild.value?.request || {};
  if (
    typeof request.provider_profile_id === "string" &&
    providerProfiles.value.some((profile) => profile.id === request.provider_profile_id)
  )
    selectedProviderId.value = request.provider_profile_id;
  if (
    typeof request.review_provider_profile_id === "string" &&
    providerProfiles.value.some((profile) => profile.id === request.review_provider_profile_id)
  )
    selectedReviewProviderId.value = request.review_provider_profile_id;
  const requestGeneration = request.generation;
  if (requestGeneration && typeof requestGeneration === "object")
    generationOverrides.value = { ...(requestGeneration as Record<string, unknown>) };
  useProfileDefaults.value = request.use_profile_defaults !== false;
  if (request.stage_limits && typeof request.stage_limits === "object")
    stageLimits.value = {
      ...stageLimits.value,
      ...(request.stage_limits as Record<string, number>),
    };
  if (request.stage_timeouts && typeof request.stage_timeouts === "object")
    stageTimeouts.value = {
      ...stageTimeouts.value,
      ...(request.stage_timeouts as Record<string, number>),
    };
  if (request.record_sizing && typeof request.record_sizing === "object")
    recordSizing.value = {
      ...recordSizing.value,
      ...(request.record_sizing as RecordSizingPolicy),
    };
  if (request.max_concurrent_requests)
    maxConcurrentRequests.value = Math.max(
      1,
      Math.min(16, Number(request.max_concurrent_requests) || 1),
    );
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
      result = await pdfCorpusApi.records(
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
    if (result.total > 0 || expected === 0)
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
  const result = await pdfCorpusApi.blocks(
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
function openFocusView() {
  if (!selectedRecord.value) return;
  focusView.value = true;
  const id = selectedRecord.value.record_id;
  if (focusHistory.value[focusHistoryIndex.value] !== id) {
    focusHistory.value = focusHistory.value.slice(0, focusHistoryIndex.value + 1);
    focusHistoryOffsets.value = focusHistoryOffsets.value.slice(0, focusHistoryIndex.value + 1);
    focusHistory.value.push(id);
    focusHistoryOffsets.value.push(recordOffset.value);
    focusHistoryIndex.value = focusHistory.value.length - 1;
  }
}
function pushFocusHistory(id: string) {
  if (!id || focusHistory.value[focusHistoryIndex.value] === id) return;
  focusHistory.value = focusHistory.value.slice(0, focusHistoryIndex.value + 1);
  focusHistoryOffsets.value = focusHistoryOffsets.value.slice(0, focusHistoryIndex.value + 1);
  focusHistory.value.push(id);
  focusHistoryOffsets.value.push(recordOffset.value);
  focusHistoryIndex.value = focusHistory.value.length - 1;
}
async function focusHistoryMove(delta: number) {
  const next = focusHistoryIndex.value + delta;
  if (next < 0 || next >= focusHistory.value.length) return;
  focusHistoryIndex.value = next;
  const id = focusHistory.value[next];
  const targetOffset = focusHistoryOffsets.value[next] ?? recordOffset.value;
  const local =
    targetOffset === recordOffset.value
      ? records.value.find((row) => row.record_id === id)
      : undefined;
  if (local) {
    selectRecord(local);
    return;
  }
  recordOffset.value = targetOffset;
  await refreshRecords(false, id);
}
async function focusQueueMove(delta: number) {
  const index = selectedRecordIndex.value;
  if (index >= 0) {
    const next = records.value[index + delta];
    if (next) {
      selectRecord(next);
      pushFocusHistory(next.record_id);
      return;
    }
  }
  if (delta > 0 && recordOffset.value + pageSize < recordTotal.value) {
    recordOffset.value += pageSize;
    await refreshRecords(false);
    const next = records.value[0];
    if (next) {
      selectRecord(next);
      pushFocusHistory(next.record_id);
    }
    return;
  }
  if (delta < 0 && recordOffset.value > 0) {
    recordOffset.value = Math.max(0, recordOffset.value - pageSize);
    await refreshRecords(false);
    const next = records.value[records.value.length - 1];
    if (next) {
      selectRecord(next);
      pushFocusHistory(next.record_id);
    }
  }
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
            await pdfCorpusApi.metadataCache(
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
    void pdfCorpusApi
      .markViewed(selectedBuildId.value, record.record_id)
      .then((result) => {
        if (selectedRecord.value?.record_id === record.record_id)
          selectedRecord.value.activity = result.activity;
      })
      .catch(() => undefined);
  void restoreReviewViewport(viewport, { record: !sameRecord });
}
function beginTextEdit(useTouchupProposal = false) {
  if (!selectedRecord.value) return;
  editingText.value = true;
  if (useTouchupProposal && selectedRecord.value.text_touchup_proposal?.proposed_text)
    textDraft.value = selectedRecord.value.text_touchup_proposal.proposed_text;
  else if (!textDraft.value) textDraft.value = String(selectedRecord.value.text || "");
}
function cancelTextEdit() {
  if (!selectedRecord.value) return;
  editingText.value = false;
  textDraft.value = String(selectedRecord.value.text || "");
  try {
    localStorage.removeItem(textDraftKey(selectedBuildId.value, selectedRecord.value.record_id));
  } catch {
    // Best effort: stale local drafts are ignored.
  }
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
async function startBuild() {
  if (!selectedAsset.value) {
    setMessage(i18n.t("pdf_corpus.choose_pdf_before_build"), "error");
    return;
  }
  busy.value = "build";
  setMessage("");
  reviewHydrated.value = false;
  hydratedTopologyCount.value = 0;
  hydratedMetadataCount.value = 0;
  records.value = [];
  recordTotal.value = 0;
  selectedRecord.value = null;
  sourceBlocks.value = [];
  try {
    const payload = {
      asset_id: selectedAssetId.value,
      auto_enrich_work_metadata: true,
      schema_id: schemaId.value,
      run_guidance: runGuidancePayload(),
      ...providerPayload.value,
      ...(handsFree.value.enabled ? { autonomous: { ...handsFree.value } } : {}),
    };
    const build = await pdfCorpusApi.createBuild(payload);
    selectedBuildId.value = build.build_id;
    currentBuild.value = build;
    registerBuildOperation(build);
    await refreshBuilds();
    startPolling();
    setMessage(i18n.t("pdf_corpus.build_started"));
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function resumeBuild() {
  if (!currentBuild.value) return;
  if (buildRunning.value) {
    setMessage(i18n.t("pdf_corpus.already_running"));
    return;
  }
  busy.value = "build";
  try {
    currentBuild.value = await pdfCorpusApi.resume(
      currentBuild.value.build_id,
      providerPayload.value,
    );
    syncBuildInRail(currentBuild.value);
    registerBuildOperation(currentBuild.value);
    startPolling();
    setMessage(i18n.t("pdf_corpus.build_resumed"));
  } catch (exc) {
    const message = exc instanceof Error ? exc.message : String(exc);
    if (message.includes("already running")) {
      await refreshBuild();
      if (currentBuild.value) registerBuildOperation(currentBuild.value);
      setMessage(i18n.t("pdf_corpus.already_running"));
    } else setMessage(message, "error");
  } finally {
    busy.value = "";
  }
}
async function retryIncompleteMetadata() {
  if (!currentBuild.value || !canRetryMetadata.value) return;
  const fields = Number(currentBuild.value.metadata_issue_summary?.auto_retry_fields || 0);
  const recordsCount = Number(
    currentBuild.value.metadata_issue_summary?.auto_retry_records || metadataIssueCount.value,
  );
  if (fields < 1) {
    setMessage(i18n.t("pdf_corpus.no_retryable_metadata"));
    return;
  }
  busy.value = "metadata-retry";
  try {
    currentBuild.value = await pdfCorpusApi.retryMetadata(
      currentBuild.value.build_id,
      providerPayload.value,
    );
    syncBuildInRail(currentBuild.value);
    registerBuildOperation(currentBuild.value);
    startPolling();
    setMessage(
      i18n.tf("pdf_corpus.metadata_retry_start_fields", { fields, records: recordsCount }),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function reviewMetadataRecord(recordId: string) {
  reviewQueue.value = "metadata";
  recordQuery.value = recordId;
  await nextTick();
  await refreshRecords(true, recordId);
  if (selectedRecord.value?.record_id === recordId) focusView.value = false;
}
async function openMetadataIssueQueue() {
  reviewQueue.value = "metadata";
  recordQuery.value = "";
  const first = currentBuild.value?.metadata_issue_summary?.records?.[0]?.record_id;
  await nextTick();
  await refreshRecords(true, first ? String(first) : "");
  await nextTick();
  recordListEl.value?.focus({ preventScroll: true });
}

function firstValidationRecordId(): string {
  const validation = currentBuild.value?.validation || {};
  const actionable = validation.validation_issues?.find((item) => item?.record_id);
  if (actionable?.record_id) return String(actionable.record_id);
  for (const key of [
    "metadata_evidence_errors",
    "metadata_schema_errors",
    "relationship_errors",
    "human_ownership_errors",
    "record_content_errors",
  ] as const) {
    const items = validation[key];
    if (!Array.isArray(items)) continue;
    const found = items.find(
      (item) => item && typeof item === "object" && "record_id" in item && item.record_id,
    );
    if (found && typeof found === "object" && "record_id" in found) return String(found.record_id);
  }
  const citation = validation.citation_errors?.find(Boolean);
  return citation ? String(citation) : "";
}

async function openValidationIssueQueue() {
  reviewQueue.value = "issues";
  recordQuery.value = "";
  const first = firstValidationRecordId();
  await nextTick();
  await refreshRecords(true, first);
  await nextTick();
  recordListEl.value?.focus({ preventScroll: true });
}
async function openRejectedQueue() {
  reviewQueue.value = "rejected";
  recordQuery.value = "";
  await nextTick();
  await refreshRecords(true);
  await nextTick();
  recordListEl.value?.focus({ preventScroll: true });
}
async function openAllReviewQueue() {
  reviewQueue.value = "all";
  recordQuery.value = "";
  await nextTick();
  await refreshRecords(true);
  await nextTick();
  recordListEl.value?.focus({ preventScroll: true });
}
function openEnrichmentFromFinish() {
  // Finish actions always mean all records; never inherit a hidden table selection.
  selectedReviewIds.value = new Set();
  llmActionProviderId.value =
    llmActionProviderId.value || selectedProviderId.value || providerProfiles.value[0]?.id || "";
  metadataEnrichmentOpen.value = true;
}
async function openSourceIssueQueue() {
  reviewQueue.value = "source";
  recordQuery.value = "";
  await nextTick();
  await refreshRecords(true);
  await nextTick();
  recordListEl.value?.focus({ preventScroll: true });
}
async function restoreAllRejected() {
  if (!currentBuild.value) return;
  busy.value = "bulk-restore";
  try {
    const result = await pdfCorpusApi.bulkDisposition(
      currentBuild.value.build_id,
      "pending",
      "rejected",
      "",
    );
    await refreshBuild();
    reviewQueue.value = "all";
    recordQuery.value = "";
    selectedRecordId.value = "";
    selectedRecord.value = null;
    await nextTick();
    await refreshRecords(true);
    setMessage(i18n.tf("pdf_corpus.restored_rejected_count", { count: result.changed }));
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function confirmManifest() {
  if (!currentBuild.value) return;
  busy.value = "manifest";
  try {
    currentBuild.value = await pdfCorpusApi.confirmManifest(
      currentBuild.value.build_id,
      providerPayload.value,
    );
    syncBuildInRail(currentBuild.value);
    registerBuildOperation(currentBuild.value);
    startPolling();
    setMessage(i18n.t("pdf_corpus.manifest_confirmed"));
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
function startPolling() {
  stopPolling();
  pollTimer = window.setInterval(async () => {
    if (!selectedBuildId.value) return;
    await refreshBuild();
    // Deterministic records are persisted before metadata enrichment. Hydrate the
    // review workspace as soon as topology exists instead of waiting for a form
    // interaction or for the entire build to stop.
    if (Number(currentBuild.value?.record_count || 0) > hydratedTopologyCount.value) {
      await nextTick();
      await refreshRecords(false, selectedRecordId.value);
    }
    const enriched = Number(currentBuild.value?.metadata_enriched_count || 0);
    if (currentBuild.value?.stage === "enriching" && enriched > hydratedMetadataCount.value) {
      hydratedMetadataCount.value = enriched;
      await nextTick();
      await refreshRecords(false, selectedRecordId.value);
    }
    if (!buildRunning.value) {
      stopPolling();
      await refreshBuilds();
      await refreshRecords(false, selectedRecordId.value);
    }
  }, 1400);
}
function stopPolling() {
  if (pollTimer !== undefined) {
    clearInterval(pollTimer);
    pollTimer = undefined;
  }
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
async function advanceFrom(recordId: string) {
  const index = records.value.findIndex((row) => row.record_id === recordId);
  const next = records.value[index + 1] || records.value[index - 1];
  if (next) {
    selectRecord(next);
    return;
  }
  if (recordOffset.value + pageSize < recordTotal.value) {
    recordOffset.value += pageSize;
    await refreshRecords();
    return;
  }
  await refreshRecords();
}
async function navigateToQueueRecord(recordId: string) {
  const existing = records.value.find((row) => row.record_id === recordId);
  if (existing) {
    selectRecord(existing);
    return;
  }
  await refreshRecords(true, recordId);
}
async function setDisposition(disposition: "pending" | "accepted" | "rejected") {
  if (reviewLocked.value) {
    setMessage(i18n.t("pdf_corpus.review_preparing_help"));
    return;
  }
  if (!currentBuild.value || !selectedRecord.value) return;
  const id = selectedRecord.value.record_id;
  if (disposition !== "pending") justProcessedRecordId.value = id;
  const viewport = captureReviewViewport();
  if (disposition !== "accepted") {
    const buildId = currentBuild.value.build_id;
    const expectedRevision = Number(selectedRecord.value.record_revision || 1);
    const row: CorpusRecord = {
      ...selectedRecord.value,
      review_disposition: disposition,
      accepted: false,
      rejected: disposition === "rejected",
      needs_review: disposition === "pending",
      record_revision: expectedRevision + 1,
    } as CorpusRecord;
    const index = records.value.findIndex((item) => item.record_id === id);
    if (reviewQueue.value !== "all" && disposition === "rejected") {
      if (index >= 0) records.value.splice(index, 1);
      recordTotal.value = Math.max(0, recordTotal.value - 1);
    } else if (index >= 0) {
      records.value.splice(index, 1, row);
    }
    selectedRecord.value = row;
    await restoreReviewViewport(viewport, { record: true, inspector: true });
    queueRecordRequest(id, ["review disposition"], async (rebase) => {
      if (disposition === "pending") {
        const result = await pdfCorpusApi.disposition(
          buildId,
          id,
          "pending",
          "",
          rebase ? undefined : expectedRevision,
        );
        applyAuthoritativeRecord(result);
        return result;
      }
      const result = await pdfCorpusApi.reviewDecision(
        buildId,
        id,
        "rejected",
        "",
        rebase ? undefined : expectedRevision,
        reviewQueue.value,
      );
      applyAuthoritativeRecord(result.record, result.build);
      return result;
    });
    return;
  }
  const buildId = currentBuild.value.build_id;
  const beforeRecords = records.value.slice();
  const beforeTotal = recordTotal.value;
  const beforeSelected = selectedRecord.value;
  const beforeSelectedId = selectedRecordId.value;
  const expectedRevision = Number(selectedRecord.value.record_revision || 1);
  const optimistic = {
    ...selectedRecord.value,
    review_disposition: "accepted" as const,
    accepted: true,
    rejected: false,
    needs_review: false,
    review_reason: "",
    record_revision: expectedRevision + 1,
  };
  const optimisticIndex = records.value.findIndex((row) => row.record_id === id);
  if (reviewQueue.value === "all" || reviewQueue.value === disposition) {
    if (optimisticIndex >= 0) records.value.splice(optimisticIndex, 1, optimistic);
  } else if (optimisticIndex >= 0) {
    records.value.splice(optimisticIndex, 1);
    recordTotal.value = Math.max(0, recordTotal.value - 1);
  }
  const nextLocal = records.value[optimisticIndex] || records.value[optimisticIndex - 1];
  if (nextLocal) selectRecord(nextLocal);
  await restoreReviewViewport(viewport, { record: true, inspector: true });
  queueRecordRequest(
    id,
    ["review disposition"],
    async (rebase) => {
      const result = await pdfCorpusApi.reviewDecision(
        buildId,
        id,
        disposition,
        "",
        rebase ? undefined : expectedRevision,
        reviewQueue.value,
      );
      currentBuild.value = result.build;
      syncBuildInRail(result.build);
      if (result.blocked) {
        records.value = beforeRecords;
        recordTotal.value = beforeTotal;
        selectedRecord.value = result.record;
        selectedRecordId.value = id;
        const idx = records.value.findIndex((row) => row.record_id === id);
        if (idx >= 0) records.value.splice(idx, 1, result.record);
        if (result.blocker === "source_problem") {
          reviewInspectorTab.value = "source";
          reviewQueue.value = "source";
          setMessage(i18n.t("pdf_corpus.accept_blocked_source"), "error");
        } else {
          reviewInspectorTab.value = "metadata";
          const fields = (result.blocking_fields || [])
            .map((field) => i18n.t(`record.${field}`, field.replace(/_/g, " ")))
            .join(", ");
          setMessage(i18n.tf("pdf_corpus.accept_blocked_metadata", { fields }));
          await nextTick();
          focusFirstMetadataBlocker();
        }
      } else {
        const idx = records.value.findIndex((row) => row.record_id === id);
        if (reviewQueue.value === "all" || reviewQueue.value === disposition) {
          if (idx >= 0) records.value.splice(idx, 1, result.record);
        }
        if (result.next_record) {
          const existing = records.value.find(
            (row) => row.record_id === result.next_record?.record_id,
          );
          if (existing) selectRecord(existing);
          else selectRecord(result.next_record);
        }
        setMessage(i18n.t("pdf_corpus.accepted_notice"));
      }
      await restoreReviewViewport(viewport, { record: true, inspector: true });
    },
    async () => {
      records.value = beforeRecords;
      recordTotal.value = beforeTotal;
      selectedRecord.value = beforeSelected;
      selectedRecordId.value = beforeSelectedId;
      await restoreReviewViewport(viewport);
    },
    false,
  );
}

async function attemptAccept() {
  if (reviewLocked.value) {
    setMessage(i18n.t("pdf_corpus.review_preparing_help"));
    return;
  }
  if (!selectedRecord.value) return;
  if (selectedRecord.value.accepted) {
    await setDisposition("pending");
    return;
  }
  // The server owns acceptance eligibility. Do not let stale client metadata
  // state turn the primary action into a no-op.
  await setDisposition("accepted");
}
async function toggleAccept() {
  await attemptAccept();
}
async function acceptFromFocus() {
  if (selectedMetadataBlocked.value) {
    focusView.value = false;
    await nextTick();
  }
  await attemptAccept();
}
async function rejectRecord() {
  await setDisposition("rejected");
}
async function skipRecord() {
  if (!selectedRecord.value) return;
  await advanceFrom(selectedRecord.value.record_id);
}
async function acceptCleanRecords() {
  if (reviewLocked.value) {
    setMessage(i18n.t("pdf_corpus.review_preparing_help"));
    return;
  }
  if (!currentBuild.value) return;
  const clean = readyCount.value;
  if (clean < 1) {
    setMessage(i18n.t("pdf_corpus.no_clean_records"));
    return;
  }
  const viewport = captureReviewViewport();
  if (!window.confirm(i18n.tf("pdf_corpus.accept_clean_confirm", { count: clean }))) return;
  busy.value = "bulk";
  try {
    const result = await pdfCorpusApi.bulkDisposition(
      currentBuild.value.build_id,
      "accepted",
      "ready",
      "",
    );
    await refreshBuild();
    reviewQueue.value = issueCount.value > 0 ? "issues" : "all";
    await nextTick();
    await refreshRecords(true);
    await restoreReviewViewport(viewport, { record: true, inspector: true });
    bulkActionFeedback.value =
      result.changed > 0
        ? i18n.tf("pdf_corpus.accept_clean_done", { count: result.changed })
        : i18n.t("pdf_corpus.accept_clean_none_changed");
    setMessage(bulkActionFeedback.value);
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function bulkDisposition(disposition: "accepted" | "rejected") {
  if (!currentBuild.value) return;
  const recordIds = Array.from(selectedReviewIds.value);
  const count = recordIds.length;
  if (!count) {
    setMessage(i18n.t("pdf_corpus.select_records_first"));
    return;
  }
  const viewport = captureReviewViewport();
  const verb =
    disposition === "accepted"
      ? i18n.t("pdf_corpus.accept_selected")
      : i18n.t("pdf_corpus.reject_selected");
  if (
    !window.confirm(
      i18n.tf("pdf_corpus.bulk_confirm", {
        action: verb,
        count,
      }),
    )
  )
    return;
  busy.value = "bulk";
  try {
    const result = await pdfCorpusApi.bulkDisposition(
      currentBuild.value.build_id,
      disposition,
      reviewQueue.value,
      recordQuery.value,
      "",
      recordIds,
    );
    selectedReviewIds.value = new Set();
    await refreshBuild();
    if (disposition === "accepted" && Number(result.blocked_metadata || 0) > 0) {
      reviewQueue.value = "metadata";
      recordQuery.value = "";
      await nextTick();
      await refreshRecords(true, result.blocked_record_ids?.[0] || "");
      reviewInspectorTab.value = "metadata";
    } else {
      await refreshRecords(true);
    }
    await restoreReviewViewport(viewport, { record: true, inspector: true });
    bulkActionFeedback.value = result.blocked_metadata
      ? i18n.tf("pdf_corpus.bulk_done_metadata_blocked", {
          count: result.changed,
          blocked: result.blocked_metadata,
        })
      : i18n.tf("pdf_corpus.bulk_done", { count: result.changed });
    setMessage(bulkActionFeedback.value);
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}

async function undoReview() {
  if (!currentBuild.value) return;
  const viewport = captureReviewViewport();
  busy.value = "record";
  try {
    const result = await pdfCorpusApi.undoReview(currentBuild.value.build_id);
    await refreshBuild();
    await refreshRecords(true, result.selected_record_id || "");
    await restoreReviewViewport(viewport, { record: true });
    setMessage(i18n.t("pdf_corpus.undo_done"));
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function redoReview() {
  if (!currentBuild.value) return;
  const viewport = captureReviewViewport();
  busy.value = "record";
  try {
    const result = await pdfCorpusApi.redoReview(currentBuild.value.build_id);
    await refreshBuild();
    await refreshRecords(true, result.selected_record_id || "");
    await restoreReviewViewport(viewport, { record: true });
    setMessage(i18n.t("pdf_corpus.redo_done"));
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function reanalyzeDocument() {
  if (!currentBuild.value) return;
  busy.value = "manifest";
  try {
    const result = await pdfCorpusApi.regenerateManifest(
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
    currentBuild.value = await pdfCorpusApi.patchManifest(
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

async function saveReviewedText(resolveIssues = resolveSourceOnTextSave.value) {
  if (!currentBuild.value || !selectedRecord.value) return;
  const recordId = selectedRecord.value.record_id;
  const viewport = captureReviewViewport();
  const buildId = currentBuild.value.build_id;
  const expectedRevision = Number(selectedRecord.value.record_revision || 1);
  const text = textDraft.value;
  const row: CorpusRecord = {
    ...selectedRecord.value,
    text,
    text_length: text.length,
    record_revision: expectedRevision + 1,
  } as CorpusRecord;
  selectedRecord.value = row;
  const index = records.value.findIndex((item) => item.record_id === recordId);
  if (index >= 0) records.value.splice(index, 1, row);
  editingText.value = false;
  resolveSourceOnTextSave.value = false;
  try {
    localStorage.removeItem(textDraftKey(selectedBuildId.value, recordId));
  } catch {
    // Best effort: browser storage must not block review.
  }
  await restoreReviewViewport(viewport, { record: true });
  queueRecordRequest(recordId, ["text"], (rebase) =>
    pdfCorpusApi.patchText(
      buildId,
      recordId,
      text,
      rebase ? undefined : expectedRevision,
      resolveIssues,
    ),
  );
}

async function markTextReviewed() {
  if (!selectedRecord.value) return;
  textDraft.value = String(selectedRecord.value.text || "");
  await saveReviewedText(false);
}

async function saveTextFromFocus(text: string, resolve: boolean) {
  textDraft.value = text;
  resolveSourceOnTextSave.value = resolve;
  await saveReviewedText(resolve);
}
async function saveSourceTranscription(text: string) {
  textDraft.value = text;
  resolveSourceOnTextSave.value = false;
  await saveReviewedText(false);
  sourceTranscriptionOpen.value = false;
}

async function saveMetadata() {
  if (!currentBuild.value || !selectedRecord.value) return;
  const viewport = captureReviewViewport();
  let changes: Record<string, unknown>;
  try {
    changes = JSON.parse(metadataDraft.value);
  } catch {
    setMessage(i18n.t("pdf_corpus.metadata_invalid"), "error");
    return;
  }
  const context = applyOptimisticMetadata(changes);
  if (!context) return;
  await restoreReviewViewport(viewport);
  queueRecordRequest(context.recordId, Object.keys(changes), (rebase) =>
    pdfCorpusApi.patchMetadata(
      context.buildId,
      context.recordId,
      changes,
      rebase ? undefined : context.expectedRevision,
    ),
  );
}
async function assignEvidenceBlock(field: string, blockId: string) {
  if (!currentBuild.value || !selectedRecord.value || !field || !blockId) return;
  const viewport = captureReviewViewport();
  selectedEvidenceField.value = field;
  const existing = selectedRecord.value.metadata_evidence?.[field];
  const ids = new Set((existing?.block_ids || []).map(String));
  if (ids.has(blockId)) {
    await restoreReviewViewport(viewport);
    return;
  }
  ids.add(blockId);
  const buildId = currentBuild.value.build_id;
  const recordId = selectedRecord.value.record_id;
  const expectedRevision = Number(selectedRecord.value.record_revision || 1);
  const evidence = {
    ...(selectedRecord.value.metadata_evidence || {}),
    [field]: {
      ...(existing || {}),
      block_ids: Array.from(ids),
      confidence: existing?.confidence ?? 1,
      reason: existing?.reason || i18n.t("pdf_corpus.human_evidence_reason"),
    },
  };
  const row: CorpusRecord = {
    ...selectedRecord.value,
    metadata_evidence: evidence,
    record_revision: expectedRevision + 1,
  } as CorpusRecord;
  selectedRecord.value = row;
  metadataDraft.value = JSON.stringify(recordMetadata(row), null, 2);
  const index = records.value.findIndex((item) => item.record_id === recordId);
  if (index >= 0) records.value.splice(index, 1, row);
  await restoreReviewViewport(viewport);
  queueRecordRequest(recordId, [field], (rebase) =>
    pdfCorpusApi.patchEvidence(
      buildId,
      recordId,
      field,
      Array.from(ids),
      existing?.confidence ?? 1,
      existing?.reason || i18n.t("pdf_corpus.human_evidence_reason"),
      rebase ? undefined : expectedRevision,
    ),
  );
}

async function toggleEvidenceBlock(blockId: string) {
  if (!currentBuild.value || !selectedRecord.value || !selectedEvidenceField.value) return;
  const viewport = captureReviewViewport();
  const field = selectedEvidenceField.value;
  const existing = selectedRecord.value.metadata_evidence?.[field];
  const ids = new Set((existing?.block_ids || []).map(String));
  if (ids.has(blockId)) ids.delete(blockId);
  else ids.add(blockId);
  const buildId = currentBuild.value.build_id;
  const recordId = selectedRecord.value.record_id;
  const expectedRevision = Number(selectedRecord.value.record_revision || 1);
  const evidence = {
    ...(selectedRecord.value.metadata_evidence || {}),
    [field]: {
      ...(existing || {}),
      block_ids: Array.from(ids),
      confidence: existing?.confidence ?? 1,
      reason: existing?.reason || i18n.t("pdf_corpus.human_evidence_reason"),
    },
  };
  const row: CorpusRecord = {
    ...selectedRecord.value,
    metadata_evidence: evidence,
    record_revision: expectedRevision + 1,
  } as CorpusRecord;
  selectedRecord.value = row;
  metadataDraft.value = JSON.stringify(recordMetadata(row), null, 2);
  const index = records.value.findIndex((item) => item.record_id === recordId);
  if (index >= 0) records.value.splice(index, 1, row);
  await restoreReviewViewport(viewport);
  queueRecordRequest(recordId, [field], (rebase) =>
    pdfCorpusApi.patchEvidence(
      buildId,
      recordId,
      field,
      Array.from(ids),
      existing?.confidence ?? 1,
      existing?.reason || i18n.t("pdf_corpus.human_evidence_reason"),
      rebase ? undefined : expectedRevision,
    ),
  );
}
async function merge(direction: "previous" | "next") {
  if (!currentBuild.value || !selectedRecord.value) return;
  const id = selectedRecord.value.record_id;
  const index = records.value.findIndex((row) => row.record_id === id);
  const neighborIndex = direction === "previous" ? index - 1 : index + 1;
  if (index < 0 || neighborIndex < 0 || neighborIndex >= records.value.length) return;
  const before = records.value.slice();
  const beforeTotal = recordTotal.value;
  const beforeSelected = selectedRecord.value;
  const firstIndex = Math.min(index, neighborIndex);
  const first = records.value[firstIndex];
  const second = records.value[Math.max(index, neighborIndex)];
  const merged: CorpusRecord = {
    ...first,
    text: [first.text, second.text].filter(Boolean).join("\n\n"),
    text_length: [first.text, second.text].filter(Boolean).join("\n\n").length,
    source_block_ids: [...(first.source_block_ids || []), ...(second.source_block_ids || [])],
    source_unit_ids: [...(first.source_unit_ids || []), ...(second.source_unit_ids || [])],
    source_spans: [...(first.source_spans || []), ...(second.source_spans || [])],
    review_disposition: "pending",
    accepted: false,
    rejected: false,
    needs_review: true,
    record_revision:
      Math.max(Number(first.record_revision || 1), Number(second.record_revision || 1)) + 1,
  };
  const viewport = captureReviewViewport();
  records.value.splice(firstIndex, 2, merged);
  recordTotal.value = Math.max(0, recordTotal.value - 1);
  selectedRecord.value = merged;
  selectedRecordId.value = merged.record_id;
  await restoreReviewViewport(viewport, { record: true });
  queueRecordRequest(
    [id, second.record_id],
    ["record boundary"],
    async () => {
      const row = await pdfCorpusApi.merge(
        currentBuild.value!.build_id,
        id,
        direction,
        Number(before.find((item) => item.record_id === id)?.record_revision || 1),
      );
      await refreshBuild();
      await refreshRecords(false, row.record_id);
      await restoreReviewViewport(viewport, { record: true });
      setMessage(
        i18n.tf("pdf_corpus.merged", {
          direction: i18n.t(`pdf_corpus.${direction}`, direction),
        }),
      );
    },
    () => {
      records.value = before;
      recordTotal.value = beforeTotal;
      selectedRecord.value = beforeSelected;
      selectedRecordId.value = beforeSelected.record_id;
    },
    false,
  );
}
async function split(afterBlockId: string) {
  if (!currentBuild.value || !selectedRecord.value) return;
  const id = selectedRecord.value.record_id;
  const targetIndex = records.value.findIndex((row) => row.record_id === id);
  const blockIds = [...(selectedRecord.value.source_block_ids || [])];
  const cut = blockIds.indexOf(afterBlockId) + 1;
  if (targetIndex < 0 || cut <= 0 || cut >= blockIds.length) return;
  const before = records.value.slice();
  const beforeTotal = recordTotal.value;
  const beforeSelected = selectedRecord.value;
  const blockText = new Map(visibleBlocks.value.map((block) => [block.block_id, block.text]));
  const textFor = (ids: string[]) =>
    ids
      .map((blockId) => blockText.get(blockId) || "")
      .filter(Boolean)
      .join("\n\n");
  const leftIds = blockIds.slice(0, cut);
  const rightIds = blockIds.slice(cut);
  const leftText = textFor(leftIds);
  const rightText = textFor(rightIds);
  if (!leftText || !rightText) return;
  const nextId = `${id}-split-pending`;
  const left: CorpusRecord = {
    ...selectedRecord.value,
    source_block_ids: leftIds,
    source_unit_ids: leftIds,
    source_spans: (selectedRecord.value.source_spans || []).filter((span) =>
      leftIds.includes(String(span.block_id || "")),
    ),
    text: leftText,
    text_length: leftText.length,
    record_revision: Number(selectedRecord.value.record_revision || 1) + 1,
    review_disposition: "pending",
    accepted: false,
    rejected: false,
    needs_review: true,
  };
  const right: CorpusRecord = {
    ...selectedRecord.value,
    record_id: nextId,
    source_block_ids: rightIds,
    source_unit_ids: rightIds,
    source_spans: (selectedRecord.value.source_spans || []).filter((span) =>
      rightIds.includes(String(span.block_id || "")),
    ),
    text: rightText,
    text_length: rightText.length,
    record_revision: 1,
    review_disposition: "pending",
    accepted: false,
    rejected: false,
    needs_review: true,
  };
  const viewport = captureReviewViewport();
  records.value.splice(targetIndex, 1, left, right);
  recordTotal.value += 1;
  selectedRecord.value = left;
  selectedRecordId.value = left.record_id;
  await restoreReviewViewport(viewport, { record: true });
  queueRecordRequest(
    [id, nextId],
    ["record boundary"],
    async () => {
      const result = await pdfCorpusApi.split(
        currentBuild.value!.build_id,
        id,
        afterBlockId,
        Number(beforeSelected.record_revision || 1),
      );
      await refreshBuild();
      await refreshRecords(false, result.records[0]?.record_id || id);
      await restoreReviewViewport(viewport, { record: true });
      setMessage(i18n.t("pdf_corpus.split_done"));
    },
    () => {
      records.value = before;
      recordTotal.value = beforeTotal;
      selectedRecord.value = beforeSelected;
      selectedRecordId.value = beforeSelected.record_id;
    },
    false,
  );
}
async function sliceRecord(
  direction: "previous" | "next" | "keep" | "new",
  offset: number,
  keepEnd?: number,
) {
  if (!currentBuild.value || !selectedRecord.value) return;
  const id = selectedRecord.value.record_id;
  if (direction === "keep") {
    const index = records.value.findIndex((row) => row.record_id === id);
    const targetText = String(selectedRecord.value.text || "");
    const previous = records.value[index - 1];
    const following = records.value[index + 1];
    if (
      index <= 0 ||
      index >= records.value.length - 1 ||
      keepEnd === undefined ||
      offset <= 0 ||
      offset >= keepEnd ||
      keepEnd > targetText.length
    )
      return;
    const prefix = targetText.slice(0, offset).trim();
    const retained = targetText.slice(offset, keepEnd).trim();
    const suffix = targetText.slice(keepEnd).trim();
    if (!prefix || !retained || !suffix) return;
    const before = records.value.slice();
    const beforeSelected = selectedRecord.value;
    const previousText = `${String(previous.text || "").trim()}\n\n${prefix}`.trim();
    const followingText = `${suffix}\n\n${String(following.text || "").trim()}`.trim();
    const nextRecord = (row: CorpusRecord, text: string): CorpusRecord => ({
      ...row,
      text,
      text_length: text.length,
      record_revision: Number(row.record_revision || 1) + 1,
      review_disposition: "pending",
      accepted: false,
      rejected: false,
      needs_review: true,
    });
    const updatedPrevious = nextRecord(previous, previousText);
    const updatedTarget = nextRecord(selectedRecord.value, retained);
    const updatedFollowing = nextRecord(following, followingText);
    const viewport = captureReviewViewport();
    records.value.splice(index - 1, 3, updatedPrevious, updatedTarget, updatedFollowing);
    selectedRecord.value = updatedTarget;
    selectedRecordId.value = id;
    await restoreReviewViewport(viewport, { record: true });
    queueRecordRequest(
      [previous.record_id, id, following.record_id],
      ["record boundary"],
      async () => {
        const result = await pdfCorpusApi.sliceRecord(
          currentBuild.value!.build_id,
          id,
          direction,
          offset,
          Number(beforeSelected.record_revision || 1),
          keepEnd,
        );
        boundarySliceOpen.value = false;
        await refreshBuild();
        await refreshRecords(false, result.record.record_id);
        await restoreReviewViewport(viewport, { record: true });
        setMessage(i18n.t("pdf_corpus.slice_done"));
      },
      () => {
        records.value = before;
        selectedRecord.value = beforeSelected;
        selectedRecordId.value = beforeSelected.record_id;
      },
      false,
    );
    return;
  }
  if (direction === "previous" || direction === "next") {
    const index = records.value.findIndex((row) => row.record_id === id);
    const neighborIndex = direction === "previous" ? index - 1 : index + 1;
    const targetText = String(selectedRecord.value.text || "");
    if (
      index < 0 ||
      neighborIndex < 0 ||
      neighborIndex >= records.value.length ||
      offset <= 0 ||
      offset >= targetText.length
    )
      return;
    const before = records.value.slice();
    const beforeSelected = selectedRecord.value;
    const neighbor = records.value[neighborIndex];
    const moved = targetText
      .slice(direction === "previous" ? 0 : offset, direction === "previous" ? offset : undefined)
      .trim();
    const retained = targetText.slice(direction === "previous" ? offset : 0).trim();
    if (!moved || !retained) return;
    const target = {
      ...selectedRecord.value,
      text: retained,
      text_length: retained.length,
      record_revision: Number(selectedRecord.value.record_revision || 1) + 1,
      review_disposition: "pending" as const,
      accepted: false,
      rejected: false,
      needs_review: true,
    };
    const neighborText =
      direction === "previous"
        ? `${String(neighbor.text || "").trim()}\n\n${moved}`.trim()
        : `${moved}\n\n${String(neighbor.text || "").trim()}`.trim();
    const updatedNeighbor = {
      ...neighbor,
      text: neighborText,
      text_length: neighborText.length,
      record_revision: Number(neighbor.record_revision || 1) + 1,
      review_disposition: "pending" as const,
      accepted: false,
      rejected: false,
      needs_review: true,
    };
    const viewport = captureReviewViewport();
    records.value.splice(
      Math.min(index, neighborIndex),
      2,
      ...(direction === "previous" ? [updatedNeighbor, target] : [target, updatedNeighbor]),
    );
    selectedRecord.value = target;
    selectedRecordId.value = id;
    await restoreReviewViewport(viewport, { record: true });
    queueRecordRequest(
      [id, neighbor.record_id],
      ["record boundary"],
      async () => {
        const result = await pdfCorpusApi.sliceRecord(
          currentBuild.value!.build_id,
          id,
          direction,
          offset,
          Number(beforeSelected.record_revision || 1),
          keepEnd,
        );
        boundarySliceOpen.value = false;
        await refreshBuild();
        await refreshRecords(false, result.record.record_id);
        await restoreReviewViewport(viewport, { record: true });
        setMessage(i18n.t("pdf_corpus.slice_done"));
      },
      () => {
        records.value = before;
        selectedRecord.value = beforeSelected;
        selectedRecordId.value = beforeSelected.record_id;
      },
      false,
    );
    return;
  }
  if (direction !== "new" || keepEnd === undefined) return;
  const index = records.value.findIndex((row) => row.record_id === id);
  const following = records.value[index + 1];
  const targetText = String(selectedRecord.value.text || "");
  if (index < 0 || !following || offset <= 0 || offset >= keepEnd || keepEnd > targetText.length)
    return;
  const prefix = targetText.slice(0, offset).trim();
  const retained = targetText.slice(offset, keepEnd).trim();
  const suffix = targetText.slice(keepEnd).trim();
  if (!prefix || !retained || !suffix) return;
  const before = records.value.slice();
  const beforeTotal = recordTotal.value;
  const beforeSelected = selectedRecord.value;
  const provisionalId = `${id}-slice-pending`;
  const revised = (row: CorpusRecord, text: string, revision: number): CorpusRecord => ({
    ...row,
    text,
    text_length: text.length,
    record_revision: revision,
    review_disposition: "pending",
    accepted: false,
    rejected: false,
    needs_review: true,
  });
  const target = revised(
    selectedRecord.value,
    prefix,
    Number(selectedRecord.value.record_revision || 1) + 1,
  );
  const created = revised({ ...selectedRecord.value, record_id: provisionalId }, retained, 1);
  const updatedFollowing = revised(
    following,
    `${suffix}\n\n${String(following.text || "").trim()}`.trim(),
    Number(following.record_revision || 1) + 1,
  );
  const viewport = captureReviewViewport();
  records.value.splice(index, 2, target, created, updatedFollowing);
  recordTotal.value = beforeTotal + 1;
  selectedRecord.value = created;
  selectedRecordId.value = provisionalId;
  await restoreReviewViewport(viewport, { record: true });
  queueRecordRequest(
    [id, provisionalId, following.record_id],
    ["record boundary"],
    async () => {
      const result = await pdfCorpusApi.sliceRecord(
        currentBuild.value!.build_id,
        id,
        "new",
        offset,
        Number(beforeSelected.record_revision || 1),
        keepEnd,
      );
      boundarySliceOpen.value = false;
      await refreshBuild();
      await refreshRecords(false, result.new_record?.record_id || result.record.record_id);
      await restoreReviewViewport(viewport, { record: true });
      setMessage(i18n.t("pdf_corpus.slice_done"));
    },
    () => {
      records.value = before;
      recordTotal.value = beforeTotal;
      selectedRecord.value = beforeSelected;
      selectedRecordId.value = beforeSelected.record_id;
    },
    false,
  );
}

async function requeueCurrentRecord() {
  if (!currentBuild.value || !selectedRecord.value) return;
  busy.value = "record";
  try {
    const availableProfileIds = new Set(providerProfiles.value.map((profile) => profile.id));
    const profileId =
      [llmActionProviderId.value, selectedProviderId.value].find(
        (id) => Boolean(id) && availableProfileIds.has(id),
      ) ||
      providerProfiles.value[0]?.id ||
      "";
    if (!profileId) throw new Error(i18n.t("pdf_corpus.no_provider_profile"));
    const actionPayload = directProfilePayloadWithModel(profileId, llmActionModel.value) || {
      provider_profile_id: profileId,
      model: llmActionModel.value || undefined,
    };
    await pdfCorpusApi.requeueMetadata(
      currentBuild.value.build_id,
      selectedRecord.value.record_id,
      actionPayload,
    );
    await refreshBuild();
    setMessage(i18n.t("pdf_corpus.requeue_requested"));
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function adjudicateBoundary(
  direction: "previous" | "next",
  profileId = llmActionProviderId.value || selectedProviderId.value,
  model = llmActionModel.value,
) {
  if (!currentBuild.value || !selectedRecord.value) return;
  const id = selectedRecord.value.record_id;
  const viewport = captureReviewViewport();
  busy.value = "boundary";
  try {
    const actionPayload = directProfilePayloadWithModel(profileId, model) || {
      provider_profile_id: profileId,
      model: model || undefined,
    };
    const result = await pdfCorpusApi.adjudicateBoundary(
      currentBuild.value.build_id,
      id,
      direction,
      actionPayload,
    );
    await refreshBuild();
    await refreshRecords(false, id);
    await restoreReviewViewport(viewport, { record: true });
    const decision = String(result.decision?.decision || "uncertain");
    setMessage(
      i18n.tf("pdf_corpus.boundary_check_done", {
        decision: i18n.t(`pdf_corpus.boundary_llm.${decision}`, decision),
      }),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function resolveMetadataField(field: string, value: unknown) {
  if (!currentBuild.value || !selectedRecord.value) return;
  rememberMetadataValues(field, value);
  const viewport = captureReviewViewport();
  metadataSavingField.value = field;
  metadataSavedField.value = "";
  const context = applyOptimisticMetadata({ [field]: value });
  if (!context) {
    metadataSavingField.value = "";
    return;
  }
  await restoreReviewViewport(viewport, { inspector: true });
  queueRecordRequest(
    context.recordId,
    [field],
    async (rebase) => {
      const result = await pdfCorpusApi.metadataDecision(
        context.buildId,
        context.recordId,
        field,
        value,
        rebase ? undefined : context.expectedRevision,
      );
      applyAuthoritativeRecord(result.record, result.build);
      if (selectedRecordId.value === context.recordId) {
        metadataSavingField.value = "";
        metadataSavedField.value = field;
      }
      return result;
    },
    () => {
      if (selectedRecordId.value === context.recordId) metadataSavingField.value = "";
    },
  );
}

async function resolveMetadataSuggestions(changes: Record<string, unknown>) {
  if (!currentBuild.value || !selectedRecord.value || !Object.keys(changes).length) return;
  for (const [field, value] of Object.entries(changes)) rememberMetadataValues(field, value);
  const viewport = captureReviewViewport();
  const context = applyOptimisticMetadata(changes);
  if (!context) return;
  await restoreReviewViewport(viewport, { inspector: true });
  queueRecordRequest(context.recordId, Object.keys(changes), async (rebase) => {
    const result = await pdfCorpusApi.metadataDecisionBatch(
      context.buildId,
      context.recordId,
      changes,
      rebase ? undefined : context.expectedRevision,
    );
    applyAuthoritativeRecord(result.record, result.build);
    return result;
  });
}

function rememberMetadataValues(field: string, value: unknown) {
  const values = Array.isArray(value) ? value : [value];
  for (const item of values) {
    if (typeof item !== "string" || !item.trim()) continue;
    (metadataHumanValues.value[field] ??= new Set()).add(item.trim());
  }
}

async function resolveMetadataNoValue(field: string) {
  if (!currentBuild.value || !selectedRecord.value) return;
  const viewport = captureReviewViewport();
  metadataSavingField.value = field;
  metadataSavedField.value = "";
  const context = applyOptimisticMetadata({ [field]: null });
  if (!context) {
    metadataSavingField.value = "";
    return;
  }
  await restoreReviewViewport(viewport, { inspector: true });
  queueRecordRequest(
    context.recordId,
    [field],
    async (rebase) => {
      const result = await pdfCorpusApi.metadataDecision(
        context.buildId,
        context.recordId,
        field,
        null,
        rebase ? undefined : context.expectedRevision,
        true,
      );
      applyAuthoritativeRecord(result.record, result.build);
      if (selectedRecordId.value === context.recordId) {
        metadataSavingField.value = "";
        metadataSavedField.value = field;
      }
      return result;
    },
    () => {
      if (selectedRecordId.value === context.recordId) metadataSavingField.value = "";
    },
  );
}
async function clearMetadataSuggestionCache() {
  if (
    !window.confirm(
      i18n.t(
        "pdf_corpus.clear_metadata_cache_confirm",
        "Clear remembered metadata suggestions? This will not change reviewed records or their history.",
      ),
    )
  )
    return;
  busy.value = "metadata-cache";
  try {
    const result = await pdfCorpusApi.clearAllMetadataCache();
    setMessage(
      i18n.tf("pdf_corpus.metadata_cache_cleared", "Cleared {count} remembered suggestion(s).", {
        count: result.cleared,
      }),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function runMetadataEnrichment(payload: {
  providerProfileId: string;
  model: string;
  families: string[];
  scope: string;
  passes: number;
  recordIds: string[];
}) {
  if (!currentBuild.value) return;
  busy.value = "metadata-enrichment";
  try {
    const actionPayload = directProfilePayloadWithModel(
      payload.providerProfileId,
      payload.model,
    ) || { provider_profile_id: payload.providerProfileId, model: payload.model || undefined };
    currentBuild.value = await pdfCorpusApi.rerunMetadataEnrichment(currentBuild.value.build_id, {
      ...actionPayload,
      families: payload.families,
      scope: payload.scope,
      passes: payload.passes,
      record_ids: payload.recordIds,
    });
    metadataEnrichmentOpen.value = false;
    syncBuildInRail(currentBuild.value);
    registerBuildOperation(currentBuild.value);
    startPolling();
    setMessage(i18n.t("pdf_corpus.metadata_enrichment_started"));
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}

async function openEditorialMemory() {
  if (!currentBuild.value) return;
  busy.value = "editorial-memory";
  try {
    editorialMemory.value = await pdfCorpusApi.editorialMemory(currentBuild.value.build_id);
    editorialMemoryOpen.value = true;
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function resetEditorialMemory() {
  if (!currentBuild.value) return;
  busy.value = "editorial-memory";
  try {
    editorialMemory.value = await pdfCorpusApi.resetEditorialMemory(currentBuild.value.build_id);
    setMessage(i18n.t("pdf_corpus.editorial_memory_reset_done"));
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}

async function openJsonlPreview() {
  if (!currentBuild.value || !selectedRecord.value) return;
  busy.value = "preview";
  try {
    const result = await pdfCorpusApi.previewRecord(
      currentBuild.value.build_id,
      selectedRecord.value.record_id,
    );
    jsonlPreview.value = {
      jsonl: result.jsonl,
      validation_errors: result.validation_errors || [],
      unresolved_fields: result.unresolved_fields || [],
      would_publish: Boolean(result.would_publish),
    };
    jsonlPreviewOpen.value = true;
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
function openLlmTouchup(text: string) {
  textDraft.value = text;
  editingText.value = true;
  llmTouchupError.value = "";
  llmTouchupResult.value = {
    source_text: selectedRecord.value?.text_touchup_proposal?.source_text || "",
    proposed_text: selectedRecord.value?.text_touchup_proposal?.proposed_text || "",
    changes: selectedRecord.value?.text_touchup_proposal?.changes || [],
    warnings: selectedRecord.value?.text_touchup_proposal?.warnings || [],
    provider: selectedRecord.value?.text_touchup_proposal?.provider || "",
    model: selectedRecord.value?.text_touchup_proposal?.model || "",
    proposal_id: selectedRecord.value?.text_touchup_proposal?.proposal_id,
    run_id: selectedRecord.value?.text_touchup_proposal?.run_id,
    created_at: selectedRecord.value?.text_touchup_proposal?.created_at,
    status: selectedRecord.value?.text_touchup_proposal?.status,
    no_change: false,
  };
  llmActionProviderId.value =
    llmActionProviderId.value || selectedProviderId.value || providerProfiles.value[0]?.id || "";
  llmActionModel.value = String(
    providerProfiles.value.find((p) => p.id === llmActionProviderId.value)?.model || "",
  );
  llmTouchupOpen.value = true;
}
async function runLlmTouchup(
  instructions = "",
  profileId = llmActionProviderId.value,
  model = llmActionModel.value,
) {
  if (!currentBuild.value || !selectedRecord.value) return;
  busy.value = "text-touchup";
  llmTouchupError.value = "";
  llmTouchupOpen.value = true;
  try {
    const actionPayload = directProfilePayloadWithModel(profileId, model) || {
      provider_profile_id: profileId,
      model: model || undefined,
    };
    const result = await pdfCorpusApi.touchupText(
      currentBuild.value.build_id,
      selectedRecord.value.record_id,
      { ...actionPayload, instructions, text: textDraft.value || selectedRecord.value.text },
    );
    llmTouchupResult.value = {
      source_text: result.source_text,
      proposed_text: result.proposed_text,
      changes: result.changes || [],
      warnings: result.warnings || [],
      provider: result.provider || "",
      model: result.model || "",
      proposal_id: result.proposal_id,
      run_id: result.run_id,
      created_at: result.created_at,
      status: "pending_review",
      no_change: Boolean(result.no_change),
    };
    selectedRecord.value = {
      ...selectedRecord.value,
      text_touchup_proposal: {
        status: "pending_review",
        proposal_id: result.proposal_id,
        run_id: result.run_id,
        source_text: result.source_text,
        proposed_text: result.proposed_text,
        changes: result.changes || [],
        warnings: result.warnings || [],
        provider: result.provider || "",
        model: result.model || "",
        created_at: result.created_at,
      },
    };
  } catch (exc) {
    llmTouchupError.value = exc instanceof Error ? exc.message : String(exc);
    setMessage(llmTouchupError.value, "error");
  } finally {
    busy.value = "";
  }
}
async function dismissLlmTouchup() {
  if (!currentBuild.value || !selectedRecord.value || !llmTouchupResult.value.proposal_id) return;
  busy.value = "text-touchup-dismiss";
  try {
    const updated = await pdfCorpusApi.setTouchupProposalStatus(
      currentBuild.value.build_id,
      selectedRecord.value.record_id,
      "dismissed",
    );
    selectedRecord.value = updated;
    const index = records.value.findIndex((row) => row.record_id === updated.record_id);
    if (index >= 0) records.value.splice(index, 1, updated);
    llmTouchupOpen.value = false;
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
function applyLlmTouchup(text: string) {
  textDraft.value = text;
  editingText.value = true;
  llmTouchupOpen.value = false;
  setMessage(i18n.t("pdf_corpus.llm_touchup_applied"));
}
function handleMetadataDirty(value: boolean) {
  metadataEditorDirty.value = value;
}

function showMetadataSource(field: string) {
  selectedEvidenceField.value = field;
  reviewInspectorTab.value = "source";
  const ids = selectedRecord.value?.metadata_evidence?.[field]?.block_ids || [];
  const first = sourceBlocks.value.find((block) => ids.includes(block.block_id));
  if (first) selectedPdfPage.value = Number(first.page || selectedPdfPage.value);
}

async function rerunMetadata() {
  if (!currentBuild.value || !selectedRecord.value) return;
  const viewport = captureReviewViewport();
  busy.value = "record";
  try {
    const profileId = llmActionProviderId.value || selectedProviderId.value;
    const payload = {
      ...(directProfilePayloadWithModel(profileId, llmActionModel.value) || {
        provider_profile_id: profileId,
        model: llmActionModel.value || undefined,
      }),
    } as Record<string, unknown>;
    if (metadataRerunFamily.value !== "all") payload.families = [metadataRerunFamily.value];
    const row = await pdfCorpusApi.rerunMetadata(
      currentBuild.value.build_id,
      selectedRecord.value.record_id,
      payload,
    );
    selectedRecord.value = row;
    metadataDraft.value = JSON.stringify(recordMetadata(row), null, 2);
    await refreshBuild();
    await refreshRecords(false, row.record_id);
    await restoreReviewViewport(viewport);
    reviewInspectorTab.value = "metadata";
    setMessage(
      metadataRerunFamily.value === "all"
        ? i18n.t("pdf_corpus.metadata_rerun")
        : i18n.tf("pdf_corpus.metadata_family_rerun", {
            family: i18n.t(
              `pdf_corpus.metadata_family.${metadataRerunFamily.value}`,
              metadataRerunFamily.value,
            ),
          }),
    );
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function publish(options: { download?: boolean; automatic?: boolean } = {}) {
  if (!currentBuild.value) return null;
  busy.value = "publish";
  try {
    const result = await pdfCorpusApi.publish(currentBuild.value.build_id);
    await refreshBuild();
    await refreshBuilds();
    setMessage(
      options.automatic
        ? i18n.tf("pdf_corpus.auto_published", { count: result.record_count })
        : i18n.tf("pdf_corpus.published", {
            count: result.record_count,
            hash: result.sha256.slice(0, 12),
          }),
    );
    if (options.download) window.location.href = pdfCorpusApi.publicationUrl(result.publication_id);
    return result;
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    return null;
  } finally {
    busy.value = "";
  }
}
async function applyBulkMetadata(payload: {
  changes: Record<string, unknown>;
  applyToAll: boolean;
}) {
  if (!currentBuild.value) return;
  busy.value = "bulk-metadata";
  try {
    const result = await pdfCorpusApi.bulkMetadata(currentBuild.value.build_id, payload.changes, {
      recordIds: payload.applyToAll ? [] : Array.from(selectedReviewIds.value),
      applyToAll: payload.applyToAll,
      reviewQueue: reviewQueue.value,
      query: recordQuery.value,
    });
    bulkMetadataOpen.value = false;
    await refreshBuild();
    await refreshRecords(false, selectedRecordId.value);
    setMessage(
      i18n.tf("pdf_corpus.bulk_metadata_applied", {
        count: result.changed,
      }),
    );
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
async function cancelBuild() {
  if (!currentBuild.value) return;
  await pdfCorpusApi.cancel(currentBuild.value.build_id);
  setMessage(i18n.t("pdf_corpus.cancel_requested"));
  startPolling();
}
async function settleMetadata() {
  if (!currentBuild.value) return;
  busy.value = "settle";
  try {
    currentBuild.value = await pdfCorpusApi.settleMetadata(currentBuild.value.build_id);
    syncBuildInRail(currentBuild.value);
    setMessage(i18n.t("pdf_corpus.settle_requested_notice"));
    startPolling();
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function previousPage() {
  if (recordOffset.value <= 0) return;
  recordOffset.value = Math.max(0, recordOffset.value - pageSize);
  await refreshRecords();
}
async function nextPage() {
  if (recordOffset.value + pageSize >= recordTotal.value) return;
  recordOffset.value += pageSize;
  await refreshRecords();
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
    if (!reviewHydrated.value || expected > hydratedTopologyCount.value || !selectedRecord.value) {
      await ensureReviewHydrated(selectedRecordId.value);
    }
  },
  { flush: "post" },
);
watch(selectedAssetId, () => {
  if (selectedAssetId.value) void refreshBuilds();
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
    <header class="builder-header">
      <div>
        <span class="eyebrow">{{ i18n.t("pdf_corpus.eyebrow") }}</span>
        <h1 id="pdf-corpus-builder-title">
          {{ i18n.t("pdf_corpus.title") }}
        </h1>
        <p>
          {{ i18n.t("pdf_corpus.subtitle") }}
        </p>
      </div>
      <div class="header-actions">
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
      </div>
    </header>

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

      <section class="setup-section setup-source-section" aria-labelledby="pdf-corpus-source-title">
        <div class="setup-section-head">
          <div>
            <span class="setup-step">A</span>
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
          :selected-asset="selectedAsset"
          :disabled="busy !== '' || buildRunning"
          :busy="busy"
          @use-current="useCurrentPdf"
          @file="upload"
          @load-url="loadSourceUrl"
          @search-gutenberg="searchGutenberg"
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
        class="setup-phase"
        aria-labelledby="pdf-corpus-structure-phase-title"
      >
        <div class="phase-label">
          <span class="setup-step">B</span>
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
        class="setup-phase"
        aria-labelledby="media-structure-phase-title"
      >
        <div class="phase-label">
          <span class="setup-step">B</span>
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

      <details class="setup-section setup-disclosure" open>
        <summary>
          <span class="setup-step">C</span
          ><span
            ><b>{{ i18n.t("pdf_corpus.llm_enrichment_title") }}</b
            ><small
              >{{ selectedProviderLabel
              }}<template v-if="selectedProfileModel"> · {{ selectedProfileModel }}</template> ·
              {{
                enrichmentMode === "deep"
                  ? i18n.t("pdf_corpus.enrichment_deep")
                  : i18n.t("pdf_corpus.enrichment_fast")
              }}</small
            ></span
          >
        </summary>
        <div class="setup-disclosure-body">
          <div class="provider-area">
            <ProviderProfileSelect
              v-model="selectedProviderId"
              :profiles="providerProfiles"
              :default-profile-id="runtime.getDefaultProviderProfileId?.() || ''"
              :label="i18n.t('pdf_corpus.provider_profile')"
              :help="i18n.t('pdf_corpus.provider_profile_help')"
              :empty-title="i18n.t('pdf_corpus.no_provider_profiles')"
              :empty-help="i18n.t('pdf_corpus.no_provider_profiles_help')"
              :manage-label="i18n.t('pdf_corpus.manage_providers')"
              :model-not-set-label="i18n.t('pdf_corpus.model_not_set')"
              :default-label="i18n.t('ui.default')"
              :concurrent-label="i18n.t('pdf_corpus.concurrent_requests')"
              :context-label="i18n.t('providers.context_tokens')"
              @manage="manageProviders"
            />
            <label
              v-if="selectedProviderId && providerProfiles.length > 1"
              class="escalation-field"
              for="pdf-corpus-review-provider"
              ><span
                ><b>{{ i18n.t("pdf_corpus.escalation_provider") }}</b
                ><small>{{ i18n.t("pdf_corpus.escalation_provider_help") }}</small></span
              ><select
                id="pdf-corpus-review-provider"
                v-model="selectedReviewProviderId"
                class="control"
              >
                <option value="">
                  {{ i18n.t("pdf_corpus.no_escalation_provider") }}
                </option>
                <option
                  v-for="profile in providerProfiles"
                  :key="profile.id"
                  :value="profile.id"
                  :disabled="profile.id === selectedProviderId"
                >
                  {{ profile.name || profile.id }} ·
                  {{ profile.model || i18n.t("pdf_corpus.model_not_set") }}
                </option>
              </select></label
            >
          </div>
          <section class="enrichment-strategy" aria-labelledby="pdf-corpus-enrichment-mode-title">
            <div class="setup-card-heading">
              <b id="pdf-corpus-enrichment-mode-title">{{
                i18n.t("pdf_corpus.enrichment_strategy")
              }}</b
              ><small>{{ i18n.t("pdf_corpus.enrichment_strategy_help") }}</small>
            </div>
            <div
              class="mode-options"
              role="radiogroup"
              :aria-label="i18n.t('pdf_corpus.enrichment_strategy')"
            >
              <label
                ><input v-model="enrichmentMode" type="radio" value="fast" /><span
                  ><b>{{ i18n.t("pdf_corpus.enrichment_fast") }}</b
                  ><small>{{ i18n.t("pdf_corpus.enrichment_fast_help") }}</small></span
                ></label
              ><label
                ><input v-model="enrichmentMode" type="radio" value="deep" /><span
                  ><b>{{ i18n.t("pdf_corpus.enrichment_deep") }}</b
                  ><small>{{ i18n.t("pdf_corpus.enrichment_deep_help") }}</small></span
                ></label
              >
            </div>
            <div v-if="enrichmentMode === 'deep'" class="included-feature">
              <b>{{ i18n.t("pdf_corpus.semantic_indexing") }}</b
              ><span>{{ i18n.t("pdf_corpus.semantic_indexing_included") }}</span>
            </div>
            <label v-else class="semantic-index-toggle"
              ><input v-model="semanticIndexing" type="checkbox" /><span
                ><b>{{ i18n.t("pdf_corpus.semantic_indexing") }}</b
                ><small>{{ i18n.t("pdf_corpus.semantic_indexing_help") }}</small></span
              ></label
            >
            <label class="semantic-index-toggle"
              ><input v-model="autoCleanText" type="checkbox" /><span
                ><b>{{ i18n.t("pdf_corpus.auto_clean_all_records") }}</b
                ><small>{{ i18n.t("pdf_corpus.auto_clean_all_records_help") }}</small></span
              ></label
            ><label class="semantic-index-toggle"
              ><input v-model="llmTouchupDuringEnrichment" type="checkbox" /><span
                ><b>{{ i18n.t("pdf_corpus.llm_touchup_during_enrichment") }}</b
                ><small>{{ i18n.t("pdf_corpus.llm_touchup_during_enrichment_help") }}</small></span
              ></label
            >
            <CorpusTextNoiseSettings
              :threshold="noiseUnusableThreshold"
              :llm-assist="llmAssessTextNoise"
              :disabled="busy !== ''"
              @update:threshold="noiseUnusableThreshold = $event"
              @update:llm-assist="llmAssessTextNoise = $event"
            />
          </section>
          <details
            v-if="!selectedProviderId"
            :open="advancedOpen"
            class="advanced-config"
            @toggle="advancedOpen = ($event.currentTarget as HTMLDetailsElement).open"
          >
            <summary>
              {{ i18n.t("pdf_corpus.manual_provider") }}
            </summary>
            <p class="help">
              {{ i18n.t("pdf_corpus.manual_provider_help") }}
            </p>
            <div class="advanced-grid">
              <label for="pdf-corpus-provider">{{ i18n.t("pdf_corpus.provider") }}</label
              ><select id="pdf-corpus-provider" v-model="manualProvider" class="control">
                <option value="ollama">Ollama</option>
                <option value="openai">
                  {{ i18n.t("pdf_corpus.openai_compatible") }}
                </option></select
              ><label for="pdf-corpus-model">{{ i18n.t("pdf_corpus.model") }}</label
              ><input
                id="pdf-corpus-model"
                v-model="manualModel"
                class="control"
                :placeholder="i18n.t('pdf_corpus.provider_default')"
              /><label for="pdf-corpus-url">{{ i18n.t("pdf_corpus.base_url") }}</label
              ><input
                id="pdf-corpus-url"
                v-model="manualBaseUrl"
                class="control"
                :placeholder="i18n.t('pdf_corpus.provider_default')"
              /><label for="pdf-corpus-key">{{ i18n.t("pdf_corpus.api_key") }}</label
              ><input
                id="pdf-corpus-key"
                v-model="manualApiKey"
                class="control"
                type="password"
                autocomplete="off"
                :placeholder="i18n.t('pdf_corpus.not_persisted')"
              />
            </div>
          </details>
        </div>
      </details>

      <details class="setup-section setup-disclosure">
        <summary>
          <span class="setup-step">D</span
          ><span
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
      <details class="setup-section setup-disclosure">
        <summary>
          <span class="setup-step">E</span
          ><span
            ><b>{{ i18n.t("schemas.title") }}</b
            ><small
              >{{ chosenSchema?.name || i18n.t("schemas.builtin")
              }}<template v-if="chosenSchema">
                ·
                {{
                  i18n.tf("schemas.field_count", {
                    count: chosenSchema.field_count,
                  })
                }}</template
              ></small
            ></span
          >
        </summary>
        <div class="setup-disclosure-body schema-choice">
          <label class="schema-choice-field"
            ><span>{{ i18n.t("schemas.choose") }}</span>
            <select v-model="schemaId" class="control" :disabled="busy !== ''">
              <option v-for="item in schemaChoices" :key="item.id" :value="item.id">
                {{ item.name }}{{ item.builtin ? ` (${i18n.t("schemas.builtin")})` : "" }}
              </option>
            </select>
            <small>{{ i18n.t("schemas.choose_help") }}</small></label
          >
          <button type="button" class="btn small" @click="schemaEditorOpen = true">
            {{ i18n.t("schemas.manage") }}
          </button>
        </div>
      </details>

      <details class="setup-section setup-disclosure">
        <summary>
          <span class="setup-step">F</span
          ><span
            ><b>{{ i18n.t("pdf_corpus.run_guidance_title") }}</b
            ><small>{{ i18n.t("pdf_corpus.run_guidance_summary") }}</small></span
          >
        </summary>
        <div class="setup-disclosure-body">
          <CorpusRunGuidance
            v-model="runGuidance"
            :fields="runGuidanceFields"
            :disabled="busy !== ''"
          />
        </div>
      </details>

      <details class="setup-section setup-disclosure">
        <summary>
          <span class="setup-step">G</span
          ><span
            ><b>{{ i18n.t("pdf_corpus.hands_free_title") }}</b
            ><small>{{
              handsFree.enabled
                ? i18n.t("pdf_corpus.hands_free_on")
                : i18n.t("pdf_corpus.hands_free_off")
            }}</small></span
          >
        </summary>
        <div class="setup-disclosure-body">
          <CorpusHandsFreeSettings v-model="handsFree" :disabled="busy !== ''" />
        </div>
      </details>

      <div class="setup-section execution-wrapper">
        <div class="setup-section-inline-head">
          <span class="setup-step">H</span
          ><span
            ><b>{{ i18n.t("pdf_corpus.advanced_execution") }}</b
            ><small>{{ i18n.t("pdf_corpus.advanced_execution_help") }}</small></span
          >
        </div>
        <CorpusExecutionSettings
          class="execution-config"
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
      </div>

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

    <div class="builder-workspace" :class="{ 'review-mode': showReviewWorkspace }">
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
                :href="pdfCorpusApi.publicationUrl(currentBuild.publication.publication_id)"
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
          <CorpusProviderSwitcher
            v-if="currentBuild && providerProfiles.length"
            :profiles="providerProfiles"
            :active-profile-id="activeBuildProfileId"
            :active-model="activeModelLabel"
            :history="currentBuild.provider_profile_history || []"
            :disabled="busy !== '' || !buildRunning"
            @change="switchBuildProvider"
          />
          <CorpusMetadataLiveStatus
            v-if="buildRunning && currentBuild?.stage === 'enriching'"
            :build="currentBuild"
            :disabled="busy !== ''"
            @settle="settleMetadata"
            @cancel="cancelBuild"
          />
          <CorpusEnrichmentPassStatus
            v-if="currentBuild"
            :build="currentBuild"
            :disabled="busy !== ''"
            @stop="cancelBuild"
            @run-another="
              llmActionProviderId =
                llmActionProviderId || selectedProviderId || providerProfiles[0]?.id || '';
              metadataEnrichmentOpen = true;
            "
          />
          <CorpusHandsFreeReport
            v-if="currentBuild"
            :report="currentBuild.autonomous_report"
            @open-record="openHandsFreeException"
          />
          <CorpusEnrichmentMetrics v-if="currentBuild" :build-id="currentBuild.build_id" />
          <CorpusTextCleanupSummary
            v-if="currentBuild?.text_cleanup"
            :summary="currentBuild.text_cleanup"
          />
          <CorpusLlmEffectivenessPanel
            v-if="currentBuild?.llm_contribution"
            :contribution="llmContribution"
            :family-effectiveness="currentBuild?.llm_family_effectiveness || {}"
            :confidence-calibration="currentBuild?.llm_confidence_calibration || {}"
            :model-effectiveness="currentBuild?.llm_model_effectiveness || {}"
            :editorial-examples-used="
              Number(currentBuild?.llm_metrics?.editorial_examples_used || 0)
            "
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
              <nav
                ref="recordListEl"
                class="records-pane"
                tabindex="-1"
                :aria-labelledby="'pdf-corpus-records-pane'"
              >
                <div class="pane-head">
                  <b id="pdf-corpus-records-pane">{{ i18n.t("pdf_corpus.review_queue") }}</b
                  ><button
                    type="button"
                    class="link-button queue-toggle"
                    @click="reviewQueueCollapsed = true"
                  >
                    {{ i18n.t("pdf_corpus.hide_queue") }}</button
                  ><label class="select-visible"
                    ><input
                      type="checkbox"
                      :checked="allVisibleSelected"
                      :disabled="!records.length || busy !== ''"
                      @change="toggleVisibleSelection(($event.target as HTMLInputElement).checked)"
                    /><span>{{ i18n.t("pdf_corpus.select_visible") }}</span></label
                  ><span>{{ recordTotal }}</span>
                </div>
                <div v-for="record in records" :key="record.record_id" class="record-row-wrap">
                  <label class="record-select"
                    ><input
                      type="checkbox"
                      :checked="selectedReviewIds.has(record.record_id)"
                      :aria-label="
                        i18n.tf('pdf_corpus.select_record_id', {
                          record: record.record_id,
                        })
                      "
                      @change="
                        toggleReviewSelection(
                          record.record_id,
                          ($event.target as HTMLInputElement).checked,
                        )
                      "
                    /><span class="sr-only">{{
                      i18n.tf("pdf_corpus.select_record_id", {
                        record: record.record_id,
                      })
                    }}</span></label
                  >
                  <button
                    type="button"
                    class="record-row"
                    :class="{ active: record.record_id === selectedRecordId }"
                    :aria-current="record.record_id === selectedRecordId ? 'true' : undefined"
                    @click="selectRecord(record)"
                  >
                    <span
                      class="record-state-icon"
                      :data-state="recordState(record)"
                      aria-hidden="true"
                      ><AppIcon v-if="recordStateIcon(record)" :name="recordStateIcon(record)"
                    /></span>
                    <span class="record-row-main"
                      ><b>{{ record.record_id }}</b
                      ><small
                        >{{ record.inline_citation }} · {{ record.text_length.toLocaleString() }}
                        {{ i18n.t("pdf_corpus.characters") }}</small
                      ><span class="record-row-status" :data-state="recordState(record)">{{
                        recordStateLabel(record)
                      }}</span
                      ><span
                        v-if="recordState(record) === 'ready' && recordLlmProcessed(record)"
                        class="record-llm-processed"
                        :title="
                          i18n.t(
                            'pdf_corpus.llm_processed_help',
                            'The metadata enrichment run finished for this record; it is now waiting for human review.',
                          )
                        "
                        ><AppIcon name="spark" />{{
                          i18n.t("pdf_corpus.llm_processed", "LLM processed")
                        }}</span
                      ><small v-if="extraIssueKinds(record).length" class="record-issue-summary">{{
                        extraIssueKinds(record)
                          .map((kind) => i18n.t(`pdf_corpus.record_state.${kind}`, kind))
                          .join(" · ")
                      }}</small></span
                    >
                  </button>
                  <button
                    v-if="recordHasSourceWarning(record)"
                    type="button"
                    class="record-source-warn"
                    :aria-label="i18n.t('pdf_corpus.source_warning_icon')"
                    @click.stop="openRecordSourceWarning(record)"
                  >
                    <AppIcon name="warning" />
                  </button>
                </div>
                <div v-if="recordsLoading && !reviewHydrated" class="rail-empty" role="status">
                  {{ i18n.t("pdf_corpus.loading_records") }}
                </div>
                <div v-else-if="!records.length" class="rail-empty">
                  {{ i18n.t("pdf_corpus.no_records_filter") }}
                  <button
                    type="button"
                    class="btn small"
                    @click="
                      reviewQueue = 'all';
                      recordQuery = '';
                    "
                  >
                    {{ i18n.t("pdf_corpus.show_all_records") }}
                  </button>
                </div>
              </nav>
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
                    :saving-field="metadataSavingField"
                    :saved-field="metadataSavedField"
                    :confidence-calibration="currentBuild?.llm_confidence_calibration || {}"
                    :known-values="metadataKnownValues"
                    @resolve="resolveMetadataField"
                    @no-value="resolveMetadataNoValue"
                    @resolve-many="resolveMetadataSuggestions"
                    @source="showMetadataSource"
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
            ? `${pdfCorpusApi.assetContentUrl(selectedAsset.asset_id)}#page=${selectedPdfPage || 1}`
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
