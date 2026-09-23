<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  pdfCorpusApi,
  type CorpusBuild,
  type CorpusRecord,
  type PdfAsset,
  type SourceBlock,
  type DocumentLayoutPlan,
  type AutonomousPolicy,
} from "../api/pdfCorpus";
import { systemApi, type ProviderProfile } from "../api/system";
import { useI18nStore } from "../stores/i18n";
import ProviderProfileSelect from "./ProviderProfileSelect.vue";
import CorpusBuildProgress from "./CorpusBuildProgress.vue";
import FieldEvidenceList from "./FieldEvidenceList.vue";
import DocumentStructureConfigurator from "./DocumentStructureConfigurator.vue";
import SourceTranscriptionDialog from "./SourceTranscriptionDialog.vue";
import CorpusSourceSummary from "./CorpusSourceSummary.vue";
import DocumentManifestEditor from "./DocumentManifestEditor.vue";
import DocumentManifestDialog from "./DocumentManifestDialog.vue";
import CorpusInitializationDialog from "./CorpusInitializationDialog.vue";
import CorpusExecutionSettings from "./CorpusExecutionSettings.vue";
import CorpusWorkflowStepper from "./CorpusWorkflowStepper.vue";
import CorpusBuildReadiness from "./CorpusBuildReadiness.vue";
import CorpusBuildHistoryMenu from "./CorpusBuildHistoryMenu.vue";
import CorpusQualitySummary from "./CorpusQualitySummary.vue";
import CorpusRecordSizingSettings from "./CorpusRecordSizingSettings.vue";
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
import CorpusSourceIssuePanel from "./CorpusSourceIssuePanel.vue";
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
import { metadataSchemasApi, type SchemaSummary } from "../api/metadataSchemas";
import CorpusHandsFreeReport from "./CorpusHandsFreeReport.vue";
import UiDialog from "./ui/UiDialog.vue";
import LlmExecutionControl from "./LlmExecutionControl.vue";
import { useCorpusBuildLifecycle } from "../composables/useCorpusBuildLifecycle";
import { useSplitter } from "../composables/useSplitter";
import AppIcon from "./AppIcon.vue";
import CorpusActionMenu, { type CorpusActionMenuItem } from "./CorpusActionMenu.vue";
import { recordState, recordIssueKinds } from "../domain/corpusReview";
import { recurringShortLines } from "../domain/textCleanup";
import * as runtime from "../runtime/runtime.js";

type MetadataPatchState = {
  record: CorpusRecord;
  build: CorpusBuild;
  queue_counts?: CorpusBuild["review_queue_counts"];
};

function isMetadataPatchState(
  result: CorpusRecord | MetadataPatchState,
): result is MetadataPatchState {
  if (!result || typeof result !== "object") return false;
  const candidate = result as { record?: unknown; build?: unknown };
  return Boolean(candidate.record && candidate.build);
}

const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const assets = ref<PdfAsset[]>([]);
const builds = ref<CorpusBuild[]>([]);
const buildsTotal = ref(0);
const providerProfiles = ref<ProviderProfile[]>([]);
const corpusProfiles = ref<Array<Record<string, unknown>>>([]);
const serverProviderIds = ref<Set<string>>(new Set());
const selectedProviderId = ref("");
const selectedReviewProviderId = ref("");
const selectedAssetId = ref("");
const selectedBuildId = ref("");
const currentBuild = ref<CorpusBuild | null>(null);
const records = ref<CorpusRecord[]>([]);
const recordTotal = ref(0);
const recordOffset = ref(0);
const pageSize = 50;
const selectedRecordId = ref("");
const selectedRecord = ref<CorpusRecord | null>(null);
const sourceBlocks = ref<SourceBlock[]>([]);
const selectedEvidenceField = ref("");
const selectedPdfPage = ref(1);
const reviewQueue = ref<ReviewQueue>("all");
// Whether the queue is hidden is remembered, so a person who wants the whole width for the record keeps it that way.
const QUEUE_KEY = "derridai.reviewQueueCollapsed";
function initialQueueCollapsed(): boolean {
  try {
    const stored = localStorage.getItem(QUEUE_KEY);
    if (stored === "1") return true;
    if (stored === "0") return false;
  } catch {
    /* private mode: start open */
  }
  return false;
}
const reviewQueueCollapsed = ref(initialQueueCollapsed());
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
async function loadSchemaChoices() {
  try {
    schemaChoices.value = (await metadataSchemasApi.list()).items;
    if (!schemaChoices.value.some((item) => item.id === schemaId.value)) schemaId.value = "default";
  } catch {
    /* the built-in schema still works without the list */
  }
}
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
    setMessage(
      i18n.t(
        "pdf_corpus.hands_free_started",
        "Hands-free run started. The report appears here when it finishes.",
      ),
    );
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
watch(reviewQueueCollapsed, (value) => {
  try {
    localStorage.setItem(QUEUE_KEY, value ? "1" : "0");
  } catch {
    /* not remembering is fine */
  }
});
const reviewInspectorTab = ref<"metadata" | "evidence" | "source">("metadata");
const reviewWorkspaceMode = ref<"record" | "metadata" | "source">("record");
const recordQuery = ref("");
const selectedReviewIds = ref<Set<string>>(new Set());
const selectedReviewCount = computed(() => selectedReviewIds.value.size);
const focusView = ref(false);
const focusHistory = ref<string[]>([]);
const focusHistoryOffsets = ref<number[]>([]);
const focusHistoryIndex = ref(-1);
const recordsLoading = ref(false);
const reviewHydrated = ref(false);
const hydratedTopologyCount = ref(0);
const hydratedMetadataCount = ref(0);
let recordRequestSerial = 0;
const recordListEl = ref<HTMLElement | null>(null);
const reviewPaneEl = ref<HTMLElement | null>(null);
const reviewInspectorEl = ref<HTMLElement | null>(null);
const busy = ref("");
const metadataSavingField = ref("");
const metadataSavedField = ref("");
const error = ref("");
const notice = ref("");
const uploadInput = ref<HTMLInputElement | null>(null);
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
        label: i18n.t("pdf_corpus.metadata_family.discourse", "Discourse / attribution"),
      },
      {
        key: "quotation",
        label: i18n.t("pdf_corpus.metadata_family.quotation", "Quotation relations"),
      },
      {
        key: "indexing",
        label: i18n.t("pdf_corpus.metadata_family.indexing", "Semantic indexing"),
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
      noiseUnusableThreshold.value = Math.max(0, Math.min(100, Number(draft.noiseUnusableThreshold)));
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

const selectedAsset = computed(
  () => assets.value.find((item) => item.asset_id === selectedAssetId.value) || null,
);
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
const reviewGridEl = ref<HTMLElement | null>(null);
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
// The queue and the inspector can be resized with the pointer or the keyboard, and are remembered.
const queueSplitter = useSplitter({
  key: "derridai.review.queueWidth",
  min: 224,
  max: 420,
  initial: 256,
  edge: "start",
  container: () => reviewGridEl.value,
});
const inspectorSplitter = useSplitter({
  key: "derridai.review.inspectorWidth",
  min: 320,
  max: 640,
  initial: 368,
  edge: "end",
  container: () => reviewGridEl.value,
});
// Secondary record actions live in a menu. An action that cannot run says why instead of just being dimmed.
function mergeUnavailable(direction: "previous" | "next"): string | undefined {
  if (busy.value !== "")
    return i18n.t("pdf_corpus.reason.busy", "Wait for the current action to finish.");
  if (structuralReviewLocked.value)
    return i18n.t(
      "pdf_corpus.reason.structure_locked",
      "Merging and slicing wait until record topology is ready.",
    );
  if (direction === "previous" && !canMergePrevious.value)
    return i18n.t("pdf_corpus.reason.no_previous", "There is no previous record to combine with.");
  if (direction === "next" && !canMergeNext.value)
    return i18n.t("pdf_corpus.reason.no_next", "There is no next record to combine with.");
  return undefined;
}
function sliceUnavailable(): string | undefined {
  if (busy.value !== "")
    return i18n.t("pdf_corpus.reason.busy", "Wait for the current action to finish.");
  if (editingText.value)
    return i18n.t("pdf_corpus.reason.finish_text_edit", "Finish or cancel the text edit first.");
  if (metadataEditorDirty.value)
    return i18n.t(
      "pdf_corpus.reason.finish_metadata_edit",
      "Save or discard the metadata changes first.",
    );
  if (!canMergePrevious.value && !canMergeNext.value)
    return i18n.t(
      "pdf_corpus.reason.no_neighbour",
      "Slicing needs a neighbouring record to move text into.",
    );
  return undefined;
}
const recordActionItems = computed<CorpusActionMenuItem[]>(() => [
  {
    id: "previous",
    label: i18n.t("pdf_corpus.combine_previous", "Combine with previous record"),
    reason: mergeUnavailable("previous"),
  },
  {
    id: "next",
    label: i18n.t("pdf_corpus.combine_next", "Combine with next record"),
    reason: mergeUnavailable("next"),
  },
  {
    id: "slice",
    label: i18n.t("pdf_corpus.slice_record", "Slice record"),
    reason: sliceUnavailable(),
  },
  { id: "preview", label: i18n.t("pdf_corpus.preview_jsonl", "Preview JSONL") },
]);
function runRecordAction(id: string) {
  if (id === "previous") merge("previous");
  else if (id === "next") merge("next");
  else if (id === "slice") boundarySliceOpen.value = true;
  else if (id === "preview") openJsonlPreview();
}
const bulkActionItems = computed<CorpusActionMenuItem[]>(() => {
  const rejectReason =
    busy.value !== ""
      ? i18n.t("pdf_corpus.reason.busy", "Wait for the current action to finish.")
      : reviewLocked.value
        ? i18n.t(
            "pdf_corpus.reason.review_locked",
            "Review is unavailable while the build is running.",
          )
        : selectedReviewCount.value === 0
          ? i18n.t("pdf_corpus.reason.select_records_first", "Select one or more records first.")
          : undefined;
  return [
    {
      id: "edit",
      label: i18n.t("pdf_corpus.bulk_edit_metadata", "Bulk edit metadata"),
      reason: busy.value !== "" ? rejectReason : reviewLocked.value ? rejectReason : undefined,
    },
    {
      id: "hands-free",
      label: i18n.t("pdf_corpus.run_hands_free", "Run hands-free…"),
      reason:
        busy.value !== ""
          ? i18n.t("pdf_corpus.reason.busy", "Wait for the current action to finish.")
          : reviewLocked.value
            ? i18n.t(
                "pdf_corpus.reason.review_locked",
                "Review is unavailable while the build is running.",
              )
            : undefined,
    },
    {
      id: "reject",
      label: i18n.tf("pdf_corpus.reject_selected_count", "Reject selected ({count})", {
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
  transientNetworkError.value
    ? i18n.t(
        "pdf_corpus.status_refresh_failed",
        "Status refresh failed. The build may still be running; DerridAI will retry automatically.",
      )
    : error.value,
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
const sourcePdfUrl = computed(() =>
  selectedAssetId.value ? pdfCorpusApi.assetContentUrl(selectedAssetId.value) : "",
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
  visibleBlocks.value.filter((block) => Number(block.page) === Number(selectedPdfPage.value)),
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
    ? ` · ${i18n.tf("pdf_corpus.record_activity_summary", "Viewed {views} · human reviews {human} · LLM reviews {llm} · enrichment passes {passes}", { views, human, llm, passes })}`
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
  if (!plan)
    return i18n.t("pdf_corpus.readiness.structure_unset", "Automatic defaults; review recommended");
  const parts: string[] = [];
  parts.push(
    plan.page_layout === "two_up"
      ? i18n.t("pdf_corpus.two_up_layout", "2 printed pages per PDF page")
      : i18n.t("pdf_corpus.single_page_layout", "1 printed page per PDF page"),
  );
  if (plan.main_text_pdf_start) {
    const printed = plan.main_text_printed_start
      ? i18n.tf("pdf_corpus.readiness.printed_anchor", " → printed p. {page}", {
          page: plan.main_text_printed_start,
        })
      : "";
    parts.push(
      i18n.tf("pdf_corpus.readiness.main_start", "Main text PDF {page}{printed}", {
        page: plan.main_text_pdf_start,
        printed,
      }),
    );
  } else parts.push(i18n.t("pdf_corpus.readiness.main_start_unset", "Main-text start not set"));
  if (plan.bibliography_pdf_start)
    parts.push(
      i18n.tf("pdf_corpus.readiness.bibliography_start", "Bibliography PDF {page}", {
        page: plan.bibliography_pdf_start,
      }),
    );
  return parts.join(" · ");
});
const setupWarnings = computed(() => {
  const warnings: string[] = [];
  if (
    selectedAsset.value?.pages?.length &&
    !selectedAsset.value.document_layout?.main_text_pdf_start
  )
    warnings.push(
      i18n.t(
        "pdf_corpus.readiness.review_structure",
        "Review document structure before building so printed-page and region defaults are explicit.",
      ),
    );
  if (selectedProviderId.value && selectedProfileActiveBuildCount.value)
    warnings.push(
      i18n.tf("pdf_corpus.profile_active_builds", "{count} active on this profile", {
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
  if (build.publication) return i18n.t("pdf_corpus.status.published_snapshot", "published");
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
    label: `PDF corpus · ${build.source_filename || "source"}`,
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

type ReviewViewport = {
  windowY: number;
  queueTop: number;
  recordTop: number;
  inspectorTop: number;
};
function captureReviewViewport(): ReviewViewport {
  return {
    windowY: window.scrollY,
    queueTop: recordListEl.value?.scrollTop || 0,
    recordTop: reviewPaneEl.value?.scrollTop || 0,
    inspectorTop: reviewInspectorEl.value?.scrollTop || 0,
  };
}
async function restoreReviewViewport(
  snapshot: ReviewViewport,
  { record = false, inspector = false }: { record?: boolean; inspector?: boolean } = {},
) {
  await nextTick();
  window.scrollTo({ top: snapshot.windowY, left: window.scrollX, behavior: "auto" });
  if (recordListEl.value) recordListEl.value.scrollTop = snapshot.queueTop;
  if (reviewPaneEl.value && !record) reviewPaneEl.value.scrollTop = snapshot.recordTop;
  if (reviewInspectorEl.value && !inspector)
    reviewInspectorEl.value.scrollTop = snapshot.inspectorTop;
}
function focusFirstMetadataBlocker() {
  reviewInspectorTab.value = "metadata";
  void nextTick(() => {
    const root = reviewInspectorEl.value;
    const field = root?.querySelector<HTMLElement>('[data-unresolved-field="true"]');
    const control = field?.querySelector<HTMLElement>(
      "input:not([disabled]),select:not([disabled]),button:not([disabled]),textarea:not([disabled])",
    );
    if (field && root) {
      const top = Math.max(0, field.offsetTop - root.offsetTop - 56);
      root.scrollTo({ top, behavior: "smooth" });
    }
    control?.focus({ preventScroll: true });
  });
}
function setReviewWorkspaceMode(mode: "record" | "metadata" | "source") {
  reviewWorkspaceMode.value = mode;
  if (mode !== "record") reviewInspectorTab.value = mode;
  void nextTick(() => {
    if (mode === "record") reviewPaneEl.value?.focus?.({ preventScroll: true });
    else reviewInspectorEl.value?.focus?.({ preventScroll: true });
  });
}
function reviewInspectorKeydown(event: KeyboardEvent) {
  const tabs = ["metadata", "evidence", "source"] as const;
  const current = tabs.indexOf(reviewInspectorTab.value);
  let next = current;
  if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
  else if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = tabs.length - 1;
  else return;
  event.preventDefault();
  reviewInspectorTab.value = tabs[next];
  void nextTick(() =>
    reviewInspectorEl.value
      ?.querySelector<HTMLElement>(`[data-review-tab="${tabs[next]}"]`)
      ?.focus({ preventScroll: true }),
  );
}
function recordMetadata(record: CorpusRecord) {
  // Keep the advanced editor packet minimal and aligned with the backend's
  // human-editable metadata contract. Operational/source/provenance fields are
  // never serialized back merely because they were present on the record.
  const editableFields = [
    "work",
    "document_title",
    "short_title",
    "original_title",
    "canonical_work_id",
    "document_author",
    "translator",
    "edition",
    "year",
    "publication_year",
    "publisher",
    "publication_place",
    "isbn",
    "document_language",
    "original_language",
    "document_is_translation",
    "language",
    "region_type",
    "region_author",
    "primary_text",
    "speaker",
    "position_holder",
    "target",
    "discourse_role",
    "proposition_status",
    "semantic_function",
    "stance",
    "claim_scope",
    "is_direct_quote",
    "quoted_speaker",
    "quoted_author",
    "quoted_work",
    "quoted_position_holder",
    "quoted_addressee",
    "quoted_referent",
    "quotation_chain",
    "topics",
    "concepts",
    "persons",
    "works_referenced",
    "needs_review",
    "review_reason",
  ];
  return Object.fromEntries(
    editableFields.filter((key) => record[key] !== undefined).map((key) => [key, record[key]]),
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
      i18n.tf(
        "pdf_corpus.profile_model_switched",
        "New metadata tasks will use {profile} / {model}. In-flight requests continue unchanged.",
        { profile: profile?.name || profileId, model: modelOverride || profile?.model || "—" },
      ),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}

async function refreshProviders() {
  const runtimeProfiles = (runtime.getProviderProfilesForUi?.() || []) as ProviderProfile[];
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
  providerProfiles.value = Array.from(merged.values());
  const defaultId = String(runtime.getDefaultProviderProfileId?.() || "");
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
      providerProfiles.value.find((profile) => profile.id === defaultId)?.id ||
      providerProfiles.value[0]?.id ||
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
async function refreshAssets() {
  const result = await pdfCorpusApi.listAssets();
  assets.value = result.items;
  if (!selectedAssetId.value && assets.value[0]) selectedAssetId.value = assets.value[0].asset_id;
}
async function refreshBuilds() {
  const result = await pdfCorpusApi.listBuilds(0, 100);
  builds.value = result.items;
  buildsTotal.value = result.total;
  const requested = String(route.query.build || "");
  if (requested && builds.value.some((build) => build.build_id === requested))
    selectedBuildId.value = requested;
  else if (!selectedBuildId.value && builds.value[0])
    selectedBuildId.value = builds.value[0].build_id;
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
  const fallback = JSON.stringify(recordMetadata(record), null, 2);
  try {
    metadataDraft.value =
      localStorage.getItem(metadataDraftKey(selectedBuildId.value, record.record_id)) || fallback;
  } catch {
    metadataDraft.value = fallback;
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

async function upload(file?: File | null) {
  if (!file) return;
  busy.value = "upload";
  setMessage("");
  try {
    const asset = await pdfCorpusApi.uploadAsset(file, "auto");
    await refreshAssets();
    selectedAssetId.value = asset.asset_id;
    setMessage(
      i18n.tf(
        "pdf_corpus.source_ingested",
        "Source ingested: {pages} pages · {blocks} source blocks · OCR on {ocr} pages.",
        { pages: asset.page_count, blocks: asset.block_count, ocr: asset.ocr_pages || 0 },
      ),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function savePageLabels(labels: Record<number, string | null>) {
  if (!selectedAssetId.value || !Object.keys(labels).length) return;
  busy.value = "page-labels";
  try {
    const asset = await pdfCorpusApi.updatePageLabels(selectedAssetId.value, labels);
    assets.value = assets.value.map((item) => (item.asset_id === asset.asset_id ? asset : item));
    setMessage(
      i18n.t(
        "pdf_corpus.page_mapping_saved",
        "Printed-page overrides saved. New corpus builds will use the corrected labels.",
      ),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function saveDocumentLayout(plan: DocumentLayoutPlan) {
  if (!selectedAssetId.value) return;
  busy.value = "document-layout";
  try {
    const asset = await pdfCorpusApi.updateDocumentLayout(selectedAssetId.value, plan);
    assets.value = assets.value.map((item) => (item.asset_id === asset.asset_id ? asset : item));
    const mapped = (asset.pages || []).filter(
      (page) =>
        Boolean(String(page.printed_page_label ?? "").trim()) ||
        (page.logical_pages || []).some((item) =>
          Boolean(String(item.printed_page_label ?? "").trim()),
        ),
    ).length;
    const exceptions = (asset.pages || []).filter((page) =>
      String(page.printed_page_label_source || "").includes("override"),
    ).length;
    setMessage(
      i18n.tf(
        "pdf_corpus.document_structure_saved_impact",
        "Document structure saved. {mapped} of {total} PDF pages are mapped; {exceptions} mapping exception(s). Deterministic page, region, and thread metadata will be used by new builds.",
        { mapped, total: asset.page_count, exceptions },
      ),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}

async function useCurrentPdf() {
  const file = runtime.state.pdf.file as File | null;
  if (!file) {
    setMessage(
      i18n.t(
        "pdf_corpus.open_pdf_first",
        "Open a PDF in Explorer first, or choose a source PDF here.",
      ),
      "error",
    );
    return;
  }
  await upload(file);
}
async function startBuild() {
  if (!selectedAsset.value) {
    setMessage(
      i18n.t(
        "pdf_corpus.choose_pdf_before_build",
        "Choose or load a source PDF before starting a corpus build.",
      ),
      "error",
    );
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
      ...providerPayload.value,
      ...(handsFree.value.enabled ? { autonomous: { ...handsFree.value } } : {}),
    };
    const build = await pdfCorpusApi.createBuild(payload);
    selectedBuildId.value = build.build_id;
    currentBuild.value = build;
    registerBuildOperation(build);
    await refreshBuilds();
    startPolling();
    setMessage(
      i18n.t(
        "pdf_corpus.build_started",
        "Corpus build started. Progress and completed checkpoints are persisted server-side.",
      ),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function resumeBuild() {
  if (!currentBuild.value) return;
  if (buildRunning.value) {
    setMessage(
      i18n.t(
        "pdf_corpus.already_running",
        "This build is already running. Its live status is shown below.",
      ),
    );
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
    setMessage(
      i18n.t("pdf_corpus.build_resumed", "Build resumed from its last completed checkpoint."),
    );
  } catch (exc) {
    const message = exc instanceof Error ? exc.message : String(exc);
    if (message.includes("already running")) {
      await refreshBuild();
      if (currentBuild.value) registerBuildOperation(currentBuild.value);
      setMessage(
        i18n.t(
          "pdf_corpus.already_running",
          "This build is already running. Its live status is shown below.",
        ),
      );
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
    setMessage(
      i18n.t(
        "pdf_corpus.no_retryable_metadata",
        "No automatically retryable metadata remains. Open the metadata issue queue for human resolution.",
      ),
    );
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
      i18n.tf(
        "pdf_corpus.metadata_retry_start_fields",
        "Retrying {fields} unresolved field(s) across {records} record(s). Topology and completed metadata are preserved.",
        { fields, records: recordsCount },
      ),
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
    setMessage(
      i18n.tf(
        "pdf_corpus.restored_rejected_count",
        "Restored {count} rejected record(s) to review.",
        { count: result.changed },
      ),
    );
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
    setMessage(
      i18n.t(
        "pdf_corpus.manifest_confirmed",
        "Document manifest confirmed. Semantic segmentation has started.",
      ),
    );
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
async function setDisposition(disposition: "pending" | "accepted" | "rejected") {
  if (reviewLocked.value) {
    setMessage(
      i18n.t(
        "pdf_corpus.review_preparing_help",
        "Metadata enrichment is still running. Records unlock individually as soon as their metadata pass finishes, so you can begin review without waiting for the entire book.",
      ),
    );
    return;
  }
  if (!currentBuild.value || !selectedRecord.value) return;
  const id = selectedRecord.value.record_id;
  const viewport = captureReviewViewport();
  busy.value = "record";
  try {
    if (disposition === "pending") {
      const updated = await pdfCorpusApi.disposition(
        currentBuild.value.build_id,
        id,
        "pending",
        "",
        Number(selectedRecord.value.record_revision || 1),
      );
      selectedRecord.value = updated;
      await refreshBuild();
      await refreshRecords(false, id);
      setMessage(i18n.t("pdf_corpus.reopened_notice", "Record reopened for review."));
    } else {
      const result = await pdfCorpusApi.reviewDecision(
        currentBuild.value.build_id,
        id,
        disposition,
        "",
        Number(selectedRecord.value.record_revision || 1),
        reviewQueue.value,
      );
      currentBuild.value = result.build;
      syncBuildInRail(result.build);
      if (result.blocked) {
        selectedRecord.value = result.record;
        const idx = records.value.findIndex((row) => row.record_id === id);
        if (idx >= 0) records.value.splice(idx, 1, result.record);
        if (result.blocker === "source_problem") {
          reviewInspectorTab.value = "source";
          reviewQueue.value = "source";
          setMessage(
            i18n.t(
              "pdf_corpus.accept_blocked_source",
              "This record has a source-extraction problem. Inspect the source, repair/rebuild, or reject the proposal.",
            ),
            "error",
          );
        } else {
          reviewInspectorTab.value = "metadata";
          const fields = (result.blocking_fields || [])
            .map((field) => i18n.t(`record.${field}`, field.replace(/_/g, " ")))
            .join(", ");
          setMessage(
            i18n.tf(
              "pdf_corpus.accept_blocked_metadata",
              "Confirm the required metadata before accepting this record: {fields}.",
              { fields },
            ),
          );
          await nextTick();
          focusFirstMetadataBlocker();
        }
      } else {
        const idx = records.value.findIndex((row) => row.record_id === id);
        if (reviewQueue.value === "all" || reviewQueue.value === disposition) {
          if (idx >= 0) records.value.splice(idx, 1, result.record);
        } else if (idx >= 0) {
          records.value.splice(idx, 1);
          recordTotal.value = Math.max(0, recordTotal.value - 1);
        }
        if (result.next_record) {
          const existing = records.value.find(
            (row) => row.record_id === result.next_record?.record_id,
          );
          if (existing) {
            selectRecord(existing);
            await nextTick();
            if (reviewPaneEl.value) reviewPaneEl.value.scrollTop = 0;
          } else if (reviewQueue.value !== "all") {
            reviewQueue.value = "all";
            await nextTick();
            await refreshRecords(true, result.next_record.record_id);
          } else {
            selectRecord(result.next_record);
          }
        } else {
          await refreshRecords(false);
        }
        setMessage(
          disposition === "accepted"
            ? i18n.t("pdf_corpus.accepted_notice", "Record accepted. Advanced to the next record.")
            : i18n.t("pdf_corpus.rejected_notice", "Record rejected. Advanced to the next record."),
        );
      }
    }
    await restoreReviewViewport(viewport, { record: true, inspector: true });
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}

async function attemptAccept() {
  if (reviewLocked.value) {
    setMessage(
      i18n.t(
        "pdf_corpus.review_preparing_help",
        "Metadata enrichment is still running. Records unlock individually as soon as their metadata pass finishes, so you can begin review without waiting for the entire book.",
      ),
    );
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
    setMessage(
      i18n.t(
        "pdf_corpus.review_preparing_help",
        "Metadata enrichment is still running. Records unlock individually as soon as their metadata pass finishes, so you can begin review without waiting for the entire book.",
      ),
    );
    return;
  }
  if (!currentBuild.value) return;
  const clean = readyCount.value;
  if (clean < 1) {
    setMessage(i18n.t("pdf_corpus.no_clean_records", "No clean records are waiting for approval."));
    return;
  }
  const viewport = captureReviewViewport();
  if (
    !window.confirm(
      i18n.tf(
        "pdf_corpus.accept_clean_confirm",
        "Accept {count} clean record(s)? Records with metadata, topology, or source problems will remain for review.",
        { count: clean },
      ),
    )
  )
    return;
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
        ? i18n.tf(
            "pdf_corpus.accept_clean_done",
            "Accepted {count} clean record(s). Only exceptions remain.",
            { count: result.changed },
          )
        : i18n.t(
            "pdf_corpus.accept_clean_none_changed",
            "No records changed. The remaining records need review or were already dispositioned.",
          );
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
    setMessage(i18n.t("pdf_corpus.select_records_first", "Select one or more records first."));
    return;
  }
  const viewport = captureReviewViewport();
  const verb =
    disposition === "accepted"
      ? i18n.t("pdf_corpus.accept_selected", "Accept selected")
      : i18n.t("pdf_corpus.reject_selected", "Reject selected");
  if (
    !window.confirm(
      i18n.tf("pdf_corpus.bulk_confirm", "{action} {count} record(s) in the current queue?", {
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
      ? i18n.tf(
          "pdf_corpus.bulk_done_metadata_blocked",
          "Accepted {count} eligible record(s); {blocked} record(s) still require metadata decisions and are now shown in the metadata queue.",
          { count: result.changed, blocked: result.blocked_metadata },
        )
      : i18n.tf("pdf_corpus.bulk_done", "Updated {count} record(s).", { count: result.changed });
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
    setMessage(i18n.t("pdf_corpus.undo_done", "The last review change was undone."));
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
    setMessage(i18n.t("pdf_corpus.redo_done", "The last undone review change was restored."));
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
        ? i18n.tf(
            "pdf_corpus.reanalyze_filled",
            "The model filled {count} missing document detail(s): {fields}.",
            { count: result.filled.length, fields: result.filled.join(", ") },
          )
        : i18n.t("pdf_corpus.reanalyze_nothing", "The model found nothing new to add."),
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
    setMessage(
      i18n.t(
        "pdf_corpus.manifest_saved",
        "Document manifest saved. Inherited record metadata and citations were regenerated for review.",
      ),
    );
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
  busy.value = "text";
  try {
    const row = await pdfCorpusApi.patchText(
      currentBuild.value.build_id,
      recordId,
      textDraft.value,
      Number(selectedRecord.value.record_revision || 1),
      resolveIssues,
    );
    selectedRecord.value = row;
    textDraft.value = String(row.text || "");
    editingText.value = false;
    resolveSourceOnTextSave.value = false;
    try {
      localStorage.removeItem(textDraftKey(selectedBuildId.value, row.record_id));
    } catch {
      // Best effort: an unavailable browser API does not block review.
    }
    const idx = records.value.findIndex((item) => item.record_id === recordId);
    if (idx >= 0) records.value.splice(idx, 1, row);
    await refreshBuild();
    await refreshRecords(false, row.record_id);
    await restoreReviewViewport(viewport, { record: true });
    setMessage(
      resolveIssues
        ? i18n.t(
            "pdf_corpus.text_saved_resolved",
            "Reviewed text saved and the record-level source issue was marked resolved. Rerun metadata if the correction affects interpretation.",
          )
        : i18n.t(
            "pdf_corpus.text_saved",
            "Reviewed text saved. The immutable extracted text remains available in Source.",
          ),
    );
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
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
    setMessage(
      i18n.t("pdf_corpus.metadata_invalid", "Metadata must be a valid JSON object."),
      "error",
    );
    return;
  }
  busy.value = "record";
  try {
    const result = await pdfCorpusApi.patchMetadata(
      currentBuild.value.build_id,
      selectedRecord.value.record_id,
      changes,
      Number(selectedRecord.value.record_revision || 1),
    );
    const row = isMetadataPatchState(result) ? result.record : result;
    selectedRecord.value = row;
    metadataDraft.value = JSON.stringify(recordMetadata(row), null, 2);
    try {
      localStorage.removeItem(metadataDraftKey(currentBuild.value.build_id, row.record_id));
    } catch {
      // Best effort: a missing stored preference uses the default.
    }
    await refreshBuild();
    await refreshRecords(false, row.record_id);
    await restoreReviewViewport(viewport);
    setMessage(
      i18n.t(
        "pdf_corpus.metadata_saved",
        "Metadata saved. Source-bound text and provenance were not modified.",
      ),
    );
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function toggleEvidenceBlock(blockId: string) {
  if (!currentBuild.value || !selectedRecord.value || !selectedEvidenceField.value) return;
  const viewport = captureReviewViewport();
  const field = selectedEvidenceField.value;
  const existing = selectedRecord.value.metadata_evidence?.[field];
  const ids = new Set((existing?.block_ids || []).map(String));
  if (ids.has(blockId)) ids.delete(blockId);
  else ids.add(blockId);
  busy.value = "evidence";
  try {
    const row = await pdfCorpusApi.patchEvidence(
      currentBuild.value.build_id,
      selectedRecord.value.record_id,
      field,
      Array.from(ids),
      existing?.confidence ?? 1,
      existing?.reason ||
        i18n.t("pdf_corpus.human_evidence_reason", "Human-reviewed evidence binding."),
      Number(selectedRecord.value.record_revision || 1),
    );
    selectedRecord.value = row;
    metadataDraft.value = JSON.stringify(recordMetadata(row), null, 2);
    await refreshBuild();
    await refreshRecords(false, row.record_id);
    await restoreReviewViewport(viewport);
    setMessage(
      i18n.t(
        "pdf_corpus.evidence_saved",
        "Evidence binding saved. The record remains open for review.",
      ),
    );
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function merge(direction: "previous" | "next") {
  if (!currentBuild.value || !selectedRecord.value) return;
  const id = selectedRecord.value.record_id;
  const viewport = captureReviewViewport();
  busy.value = "record";
  try {
    const row = await pdfCorpusApi.merge(
      currentBuild.value.build_id,
      id,
      direction,
      Number(selectedRecord.value.record_revision || 1),
    );
    await refreshBuild();
    await refreshRecords(false, row.record_id);
    await restoreReviewViewport(viewport, { record: true });
    setMessage(
      i18n.tf(
        "pdf_corpus.merged",
        "Merged with {direction} record; the merged boundary now requires review.",
        { direction: i18n.t(`pdf_corpus.${direction}`, direction) },
      ),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function split(afterBlockId: string) {
  if (!currentBuild.value || !selectedRecord.value) return;
  const id = selectedRecord.value.record_id;
  const viewport = captureReviewViewport();
  busy.value = "record";
  try {
    const result = await pdfCorpusApi.split(
      currentBuild.value.build_id,
      id,
      afterBlockId,
      Number(selectedRecord.value.record_revision || 1),
    );
    await refreshBuild();
    await refreshRecords(false, result.records[0]?.record_id || id);
    await restoreReviewViewport(viewport, { record: true });
    setMessage(
      i18n.t(
        "pdf_corpus.split_done",
        "Record split at the selected semantic source boundary. Both records require review.",
      ),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}
async function sliceRecord(
  direction: "previous" | "next" | "keep" | "new",
  offset: number,
  keepEnd?: number,
) {
  if (!currentBuild.value || !selectedRecord.value) return;
  const id = selectedRecord.value.record_id;
  const viewport = captureReviewViewport();
  busy.value = "record";
  try {
    const result = await pdfCorpusApi.sliceRecord(
      currentBuild.value.build_id,
      id,
      direction,
      offset,
      Number(selectedRecord.value.record_revision || 1),
      keepEnd,
    );
    boundarySliceOpen.value = false;
    await refreshBuild();
    await refreshRecords(false, result.record.record_id);
    await restoreReviewViewport(viewport, { record: true });
    setMessage(
      i18n.t(
        "pdf_corpus.slice_done",
        "Boundary adjusted. Both neighboring records were reopened for review and affected metadata was marked stale.",
      ),
    );
  } catch (exc) {
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
}

async function requeueCurrentRecord() {
  if (!currentBuild.value || !selectedRecord.value) return;
  busy.value = "record";
  try {
    await pdfCorpusApi.requeueMetadata(
      currentBuild.value.build_id,
      selectedRecord.value.record_id,
      {
        provider_profile_id: llmActionProviderId.value || selectedProviderId.value,
        model: llmActionModel.value || undefined,
      },
    );
    await refreshBuild();
    setMessage(
      i18n.t(
        "pdf_corpus.requeue_requested",
        "Record queued at the front of the current enrichment run; its review feedback will inform later records.",
      ),
    );
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
      i18n.tf("pdf_corpus.boundary_check_done", "Boundary second-reader result: {decision}.", {
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
  busy.value = "metadata-field";
  const recordId = selectedRecord.value.record_id;
  try {
    const result = await pdfCorpusApi.metadataDecision(
      currentBuild.value.build_id,
      recordId,
      field,
      value,
      Number(selectedRecord.value.record_revision || 1),
    );
    selectedRecord.value = result.record;
    currentBuild.value = result.build;
    syncBuildInRail(result.build);
    if (result.queue_counts) currentBuild.value.review_queue_counts = result.queue_counts;
    metadataDraft.value = JSON.stringify(recordMetadata(result.record), null, 2);
    const idx = records.value.findIndex((row) => row.record_id === recordId);
    if (idx >= 0) records.value.splice(idx, 1, result.record);
    metadataSavedField.value = field;
    metadataEditorDirty.value = false;
    const remaining = result.remaining_fields || [];
    if (remaining.length === 0) {
      // Keep the resolved record on screen even if the active exception queue no
      // longer contains it. The reviewer should make one final record-level
      // decision instead of hunting for the same record in another queue.
      setMessage(
        i18n.t(
          "pdf_corpus.metadata_resolved_ready",
          "Metadata confirmed. Review the record, then choose Accept & next or Reject & next.",
        ),
      );
      await nextTick();
      acceptButtonEl.value?.focus({ preventScroll: true });
    } else {
      setMessage(
        i18n.tf(
          "pdf_corpus.metadata_field_confirmed",
          "Confirmed {field}. {count} metadata decision(s) remain for this record.",
          { field: i18n.t(`record.${field}`, field.replace(/_/g, " ")), count: remaining.length },
        ),
      );
    }
    await restoreReviewViewport(viewport, { inspector: true });
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
    metadataSavingField.value = "";
  }
}

async function resolveMetadataSuggestions(changes: Record<string, unknown>) {
  if (!currentBuild.value || !selectedRecord.value || !Object.keys(changes).length) return;
  for (const [field, value] of Object.entries(changes)) rememberMetadataValues(field, value);
  const viewport = captureReviewViewport();
  busy.value = "metadata-suggestions";
  try {
    const result = await pdfCorpusApi.patchMetadata(
      currentBuild.value.build_id,
      selectedRecord.value.record_id,
      changes,
      Number(selectedRecord.value.record_revision || 1),
      true,
    );
    const row = isMetadataPatchState(result) ? result.record : result;
    if (isMetadataPatchState(result)) currentBuild.value = result.build;
    selectedRecord.value = row;
    const idx = records.value.findIndex((item) => item.record_id === row.record_id);
    if (idx >= 0) records.value.splice(idx, 1, row);
    metadataDraft.value = JSON.stringify(recordMetadata(row), null, 2);
    metadataEditorDirty.value = false;
    await restoreReviewViewport(viewport, { inspector: true });
    setMessage(
      i18n.tf(
        "pdf_corpus.llm_suggestions_saved",
        "Saved {count} LLM suggestion(s) as human-confirmed metadata.",
        { count: Object.keys(changes).length },
      ),
    );
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
  }
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
  busy.value = "metadata-field";
  try {
    const result = await pdfCorpusApi.metadataDecision(
      currentBuild.value.build_id,
      selectedRecord.value.record_id,
      field,
      null,
      Number(selectedRecord.value.record_revision || 1),
      true,
    );
    selectedRecord.value = result.record;
    currentBuild.value = result.build;
    syncBuildInRail(result.build);
    metadataDraft.value = JSON.stringify(recordMetadata(result.record), null, 2);
    const idx = records.value.findIndex((row) => row.record_id === result.record.record_id);
    if (idx >= 0) records.value.splice(idx, 1, result.record);
    metadataEditorDirty.value = false;
    setMessage(
      i18n.t(
        "pdf_corpus.no_supported_value_confirmed",
        "Confirmed that no supported value applies to this field.",
      ),
    );
    await restoreReviewViewport(viewport, { inspector: true });
  } catch (exc) {
    await restoreReviewViewport(viewport);
    setMessage(exc instanceof Error ? exc.message : String(exc), "error");
  } finally {
    busy.value = "";
    metadataSavingField.value = "";
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
    setMessage(
      i18n.t(
        "pdf_corpus.metadata_enrichment_started",
        "Metadata enrichment pass started. Accepted records will reopen only when new or disputed metadata needs review.",
      ),
    );
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
    setMessage(
      i18n.t(
        "pdf_corpus.editorial_memory_reset_done",
        "Editorial memory reset. Existing human decisions remain authoritative, but only later decisions will guide future LLM calls.",
      ),
    );
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
  setMessage(
    i18n.t(
      "pdf_corpus.llm_touchup_applied",
      "LLM touch-up applied to the local draft. Review it, then save to make it authoritative.",
    ),
  );
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
        ? i18n.t(
            "pdf_corpus.metadata_rerun",
            "Interpretive metadata rerun against the current reviewed record text.",
          )
        : i18n.tf(
            "pdf_corpus.metadata_family_rerun",
            "{family} metadata rerun against the current reviewed record text.",
            {
              family: i18n.t(
                `pdf_corpus.metadata_family.${metadataRerunFamily.value}`,
                metadataRerunFamily.value,
              ),
            },
          ),
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
        ? i18n.tf(
            "pdf_corpus.auto_published",
            "Review complete. Published {count} records automatically.",
            { count: result.record_count },
          )
        : i18n.tf("pdf_corpus.published", "Published {count} records · SHA-256 {hash}…", {
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
      i18n.tf("pdf_corpus.bulk_metadata_applied", "Updated metadata on {count} record(s).", {
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
  setMessage(
    i18n.t(
      "pdf_corpus.cancel_requested",
      "Cancellation requested. The segmented workspace remains editable, and you can start another build after cancellation settles.",
    ),
  );
  startPolling();
}
async function settleMetadata() {
  if (!currentBuild.value) return;
  busy.value = "settle";
  try {
    currentBuild.value = await pdfCorpusApi.settleMetadata(currentBuild.value.build_id);
    syncBuildInRail(currentBuild.value);
    setMessage(
      i18n.t(
        "pdf_corpus.settle_requested_notice",
        "Remaining automatic metadata tasks will settle as review exceptions after any active request reaches its deadline.",
      ),
    );
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
  const target = event.target as HTMLElement | null;
  if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
  if (event.key.toLowerCase() === "a") {
    event.preventDefault();
    void attemptAccept();
  } else if (event.key.toLowerCase() === "r") {
    event.preventDefault();
    void setDisposition("rejected");
  } else if (event.key.toLowerCase() === "z") {
    event.preventDefault();
    void undoReview();
  } else if (event.key.toLowerCase() === "j" || event.key === "ArrowDown") {
    event.preventDefault();
    void skipRecord();
  } else if (event.key.toLowerCase() === "f") {
    event.preventDefault();
    focusView.value = !focusView.value;
  }
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
</script>

<template>
  <section class="corpus-builder" :aria-labelledby="'pdf-corpus-builder-title'">
    <header class="builder-header">
      <div>
        <span class="eyebrow">{{ i18n.t("pdf_corpus.eyebrow", "Corpus Builder") }}</span>
        <h1 id="pdf-corpus-builder-title">
          {{ i18n.t("pdf_corpus.title", "Build auditable records from source PDFs") }}
        </h1>
        <p>
          {{
            i18n.t(
              "pdf_corpus.subtitle",
              "Deterministic extraction and provenance come first. Targeted LLM enrichment is optional, measurable, and used only where it can add scholarly value.",
            )
          }}
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
              ? i18n.t("pdf_corpus.start_concurrent_build", "Start another build")
              : i18n.t("pdf_corpus.start_new_build", "Start new build")
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
          :aria-label="i18n.t('ui.dismiss', 'Dismiss')"
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
        {{ i18n.t("pdf_corpus.build_configuration", "Build configuration") }}
      </h2>

      <section class="setup-section setup-source-section" aria-labelledby="pdf-corpus-source-title">
        <div class="setup-section-head">
          <div>
            <span class="setup-step">A</span>
            <div>
              <h3 id="pdf-corpus-source-title">
                {{ i18n.t("pdf_corpus.source_setup_title", "Source PDF") }}
              </h3>
              <p>
                {{
                  i18n.t(
                    "pdf_corpus.source_setup_help",
                    "Choose an extracted PDF, or add the PDF currently open in Explorer.",
                  )
                }}
              </p>
            </div>
          </div>
        </div>
        <div class="source-setup-grid">
          <label for="pdf-corpus-source"
            ><span>{{ i18n.t("pdf_corpus.source_asset", "Source asset") }}</span
            ><select id="pdf-corpus-source" v-model="selectedAssetId" class="control">
              <option value="">
                {{ i18n.t("pdf_corpus.choose_persisted_pdf", "Choose a persisted PDF…") }}
              </option>
              <option v-for="asset in assets" :key="asset.asset_id" :value="asset.asset_id">
                {{ asset.filename }} · {{ asset.page_count }} pp · {{ asset.block_count }}
                {{ i18n.t("pdf_corpus.source_units", "source units") }}
              </option>
            </select></label
          >
          <div class="source-actions">
            <button
              type="button"
              class="btn"
              @click="useCurrentPdf"
              :disabled="busy !== '' || buildRunning"
            >
              {{ i18n.t("pdf_corpus.use_current_pdf", "Use current Explorer PDF") }}</button
            ><button
              type="button"
              class="btn"
              @click="uploadInput?.click()"
              :disabled="busy !== '' || buildRunning"
            >
              {{
                busy === "upload"
                  ? i18n.t("pdf_corpus.extracting", "Extracting…")
                  : i18n.t("pdf_corpus.choose_pdf", "Choose source PDF")
              }}</button
            ><input
              ref="uploadInput"
              class="sr-only"
              type="file"
              accept="application/pdf,.pdf"
              :aria-label="i18n.t('pdf_corpus.choose_pdf', 'Choose source PDF')"
              @change="upload(($event.target as HTMLInputElement).files?.[0])"
            />
          </div>
        </div>
        <div v-if="selectedAsset" class="source-facts">
          <span>{{ selectedAsset.page_count }} {{ i18n.t("pdf_corpus.pages", "pages") }}</span
          ><span
            >{{ selectedAsset.block_count }}
            {{ i18n.t("pdf_corpus.source_units", "source units") }}</span
          ><span
            >{{ selectedAsset.ocr_pages }} {{ i18n.t("pdf_corpus.ocr_pages", "OCR page(s)") }}</span
          ><span v-if="selectedAsset.metadata?.author"
            ><b>{{ i18n.t("pdf_corpus.pdf_author", "PDF author") }}</b
            >: {{ String(selectedAsset.metadata.author) }}</span
          ><span>SHA-256 {{ selectedAsset.sha256.slice(0, 16) }}…</span
          ><span>{{ formatDate(selectedAsset.created_at) }}</span>
        </div>
        <p v-if="selectedAsset" class="source-facts-help">
          {{
            i18n.t(
              "pdf_corpus.source_facts_help",
              "Blocks are extracted text layout units, not records. OCR page(s) counts pages where OCR was used; zero means the PDF text layer was used directly. An embedded PDF author is a deterministic candidate and remains reviewable in the document manifest.",
            )
          }}
        </p>
      </section>

      <section
        v-if="selectedAsset?.pages?.length"
        class="setup-phase"
        aria-labelledby="pdf-corpus-structure-phase-title"
      >
        <div class="phase-label">
          <span class="setup-step">B</span>
          <div>
            <h3 id="pdf-corpus-structure-phase-title">
              {{ i18n.t("pdf_corpus.document_structure", "Document structure & pagination") }}
            </h3>
            <p>
              {{
                i18n.t(
                  "pdf_corpus.structure_before_build_help",
                  "Set physical-to-printed page rules before record construction so deterministic pagination, regions, and threads have an explicit source of truth.",
                )
              }}
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

      <details class="setup-section setup-disclosure" open>
        <summary>
          <span class="setup-step">C</span
          ><span
            ><b>{{ i18n.t("pdf_corpus.llm_enrichment_title", "LLM & enrichment") }}</b
            ><small
              >{{ selectedProviderLabel
              }}<template v-if="selectedProfileModel"> · {{ selectedProfileModel }}</template> ·
              {{
                enrichmentMode === "deep"
                  ? i18n.t("pdf_corpus.enrichment_deep", "Deep scholarly enrichment")
                  : i18n.t("pdf_corpus.enrichment_fast", "Fast corpus build")
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
              :label="i18n.t('pdf_corpus.provider_profile', 'Primary LLM provider')"
              :help="
                i18n.t(
                  'pdf_corpus.provider_profile_help',
                  'Use a centrally managed provider profile. Its model and generation defaults remain reusable across DerridAI workflows.',
                )
              "
              :empty-title="
                i18n.t('pdf_corpus.no_provider_profiles', 'No LLM provider profiles are configured')
              "
              :empty-help="
                i18n.t(
                  'pdf_corpus.no_provider_profiles_help',
                  'Create a provider profile or use the manual compatibility settings below.',
                )
              "
              :manage-label="i18n.t('pdf_corpus.manage_providers', 'Manage provider profiles')"
              :model-not-set-label="i18n.t('pdf_corpus.model_not_set', 'model not set')"
              :default-label="i18n.t('ui.default', 'Default')"
              :concurrent-label="
                i18n.t('pdf_corpus.concurrent_requests', 'max concurrent request(s)')
              "
              :context-label="i18n.t('providers.context_tokens', 'context tokens')"
              @manage="manageProviders"
            />
            <label
              v-if="selectedProviderId && providerProfiles.length > 1"
              class="escalation-field"
              for="pdf-corpus-review-provider"
              ><span
                ><b>{{ i18n.t("pdf_corpus.escalation_provider", "Escalation provider") }}</b
                ><small>{{
                  i18n.t(
                    "pdf_corpus.escalation_provider_help",
                    "Optional fallback used only after the primary provider exhausts structured-output retries.",
                  )
                }}</small></span
              ><select
                id="pdf-corpus-review-provider"
                v-model="selectedReviewProviderId"
                class="control"
              >
                <option value="">
                  {{
                    i18n.t(
                      "pdf_corpus.no_escalation_provider",
                      "None — keep failures for human review",
                    )
                  }}
                </option>
                <option
                  v-for="profile in providerProfiles"
                  :key="profile.id"
                  :value="profile.id"
                  :disabled="profile.id === selectedProviderId"
                >
                  {{ profile.name || profile.id }} ·
                  {{ profile.model || i18n.t("pdf_corpus.model_not_set", "model not set") }}
                </option>
              </select></label
            >
          </div>
          <section class="enrichment-strategy" aria-labelledby="pdf-corpus-enrichment-mode-title">
            <div class="setup-card-heading">
              <b id="pdf-corpus-enrichment-mode-title">{{
                i18n.t("pdf_corpus.enrichment_strategy", "Enrichment strategy")
              }}</b
              ><small>{{
                i18n.t(
                  "pdf_corpus.enrichment_strategy_help",
                  "Fast mode routes only genuinely useful metadata questions to the LLM. Deep mode runs broader attribution, quotation, and indexing analysis.",
                )
              }}</small>
            </div>
            <div
              class="mode-options"
              role="radiogroup"
              :aria-label="i18n.t('pdf_corpus.enrichment_strategy', 'Enrichment strategy')"
            >
              <label
                ><input v-model="enrichmentMode" type="radio" value="fast" /><span
                  ><b>{{ i18n.t("pdf_corpus.enrichment_fast", "Fast corpus build") }}</b
                  ><small>{{
                    i18n.t(
                      "pdf_corpus.enrichment_fast_help",
                      "Deterministic metadata first; quotation analysis only when signaled; semantic indexing off unless enabled below.",
                    )
                  }}</small></span
                ></label
              ><label
                ><input v-model="enrichmentMode" type="radio" value="deep" /><span
                  ><b>{{ i18n.t("pdf_corpus.enrichment_deep", "Deep scholarly enrichment") }}</b
                  ><small>{{
                    i18n.t(
                      "pdf_corpus.enrichment_deep_help",
                      "Runs discourse, quotation, and semantic indexing more broadly. Slower and intended for deliberate enrichment work.",
                    )
                  }}</small></span
                ></label
              >
            </div>
            <div v-if="enrichmentMode === 'deep'" class="included-feature">
              <b>{{ i18n.t("pdf_corpus.semantic_indexing", "Semantic indexing") }}</b
              ><span>{{
                i18n.t("pdf_corpus.semantic_indexing_included", "Included in Deep enrichment")
              }}</span>
            </div>
            <label v-else class="semantic-index-toggle"
              ><input v-model="semanticIndexing" type="checkbox" /><span
                ><b>{{ i18n.t("pdf_corpus.semantic_indexing", "Semantic indexing") }}</b
                ><small>{{
                  i18n.t(
                    "pdf_corpus.semantic_indexing_help",
                    "Generate topics, concepts, persons, and referenced works. Deep mode always includes indexing.",
                  )
                }}</small></span
              ></label
            >
            <label class="semantic-index-toggle"
              ><input v-model="autoCleanText" type="checkbox" /><span
                ><b>{{
                  i18n.t(
                    "pdf_corpus.auto_clean_all_records",
                    "Clean all record text before enrichment",
                  )
                }}</b
                ><small>{{
                  i18n.t(
                    "pdf_corpus.auto_clean_all_records_help",
                    "Recommended. Removes repeated headers and page numbers, repairs prose line wrapping, trims blank-line noise and obvious OCR artifacts while preserving immutable extracted text for audit.",
                  )
                }}</small></span
              ></label
            ><label class="semantic-index-toggle"
              ><input v-model="llmTouchupDuringEnrichment" type="checkbox" /><span
                ><b>{{
                  i18n.t(
                    "pdf_corpus.llm_touchup_during_enrichment",
                    "Use LLM to touch-up text as part of enrichment",
                  )
                }}</b
                ><small>{{
                  i18n.t(
                    "pdf_corpus.llm_touchup_during_enrichment_help",
                    "Proposes conservative corrections for errata, diacritics, formatting, quotations, and line breaks. Nothing becomes authoritative until you review and save the proposal.",
                  )
                }}</small></span
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
              {{ i18n.t("pdf_corpus.manual_provider", "Manual provider compatibility settings") }}
            </summary>
            <p class="help">
              {{
                i18n.t(
                  "pdf_corpus.manual_provider_help",
                  "Used only when no provider profile is selected. Provider profiles are recommended because credentials remain server-owned and resumable builds can reuse the same configuration.",
                )
              }}
            </p>
            <div class="advanced-grid">
              <label for="pdf-corpus-provider">{{
                i18n.t("pdf_corpus.provider", "Provider")
              }}</label
              ><select id="pdf-corpus-provider" v-model="manualProvider" class="control">
                <option value="ollama">Ollama</option>
                <option value="openai">
                  {{ i18n.t("pdf_corpus.openai_compatible", "OpenAI-compatible") }}
                </option></select
              ><label for="pdf-corpus-model">{{ i18n.t("pdf_corpus.model", "Model") }}</label
              ><input
                id="pdf-corpus-model"
                v-model="manualModel"
                class="control"
                :placeholder="i18n.t('pdf_corpus.provider_default', 'Provider default')"
              /><label for="pdf-corpus-url">{{ i18n.t("pdf_corpus.base_url", "Base URL") }}</label
              ><input
                id="pdf-corpus-url"
                v-model="manualBaseUrl"
                class="control"
                :placeholder="i18n.t('pdf_corpus.provider_default', 'Provider default')"
              /><label for="pdf-corpus-key">{{ i18n.t("pdf_corpus.api_key", "API key") }}</label
              ><input
                id="pdf-corpus-key"
                v-model="manualApiKey"
                class="control"
                type="password"
                autocomplete="off"
                :placeholder="i18n.t('pdf_corpus.not_persisted', 'Not persisted in build manifest')"
              />
            </div>
          </details>
        </div>
      </details>

      <details class="setup-section setup-disclosure">
        <summary>
          <span class="setup-step">D</span
          ><span
            ><b>{{ i18n.t("pdf_corpus.record_construction", "Record construction") }}</b
            ><small>{{
              i18n.tf("pdf_corpus.readiness.sizing", "{target} ± {tolerance} characters", {
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
            ><b>{{ i18n.t("schemas.title", "Metadata schema") }}</b
            ><small
              >{{ chosenSchema?.name || i18n.t("schemas.builtin", "Built in")
              }}<template v-if="chosenSchema">
                ·
                {{
                  i18n.tf("schemas.field_count", "{count} fields", {
                    count: chosenSchema.field_count,
                  })
                }}</template
              ></small
            ></span
          >
        </summary>
        <div class="setup-disclosure-body schema-choice">
          <label class="schema-choice-field"
            ><span>{{ i18n.t("schemas.choose", "Metadata schema") }}</span>
            <select v-model="schemaId" class="control" :disabled="busy !== ''">
              <option v-for="item in schemaChoices" :key="item.id" :value="item.id">
                {{ item.name
                }}{{ item.builtin ? ` (${i18n.t("schemas.builtin", "Built in")})` : "" }}
              </option>
            </select>
            <small>{{
              i18n.t(
                "schemas.choose_help",
                "The metadata fields on every record and what the model looks for in each. The build keeps its own copy.",
              )
            }}</small></label
          >
          <button type="button" class="btn small" @click="schemaEditorOpen = true">
            {{ i18n.t("schemas.manage", "Manage schemas…") }}
          </button>
        </div>
      </details>

      <details class="setup-section setup-disclosure">
        <summary>
          <span class="setup-step">F</span
          ><span
            ><b>{{ i18n.t("pdf_corpus.hands_free_title", "Hands-free mode") }}</b
            ><small>{{
              handsFree.enabled
                ? i18n.t(
                    "pdf_corpus.hands_free_on",
                    "On: the build settles itself, then reports what is left",
                  )
                : i18n.t("pdf_corpus.hands_free_off", "Off: you review every record")
            }}</small></span
          >
        </summary>
        <div class="setup-disclosure-body">
          <CorpusHandsFreeSettings v-model="handsFree" :disabled="busy !== ''" />
        </div>
      </details>

      <div class="setup-section execution-wrapper">
        <div class="setup-section-inline-head">
          <span class="setup-step">G</span
          ><span
            ><b>{{ i18n.t("pdf_corpus.advanced_execution", "Advanced execution") }}</b
            ><small>{{
              i18n.t(
                "pdf_corpus.advanced_execution_help",
                "Provider generation parameters, concurrency, stage budgets, and deadlines.",
              )
            }}</small></span
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
      <summary>{{ i18n.t("pdf_corpus.build_settings_summary", "Build settings") }}</summary>
      <div>
        <span>{{ currentBuild.source_filename }}</span
        ><span
          >{{ i18n.t("pdf_corpus.provider_profile", "Provider profile") }}:
          {{ activeProviderProfileLabel }}</span
        ><span>{{ i18n.t("pdf_corpus.model", "Model") }}: {{ activeModelLabel }}</span
        ><button
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

    <div class="builder-workspace" :class="{ 'review-mode': showReviewWorkspace && !finishPhase }">
      <aside
        v-if="!showReviewWorkspace || finishPhase"
        class="build-rail"
        :aria-label="i18n.t('pdf_corpus.builds', 'Corpus builds')"
      >
        <div class="rail-title">
          <div>
            <b>{{ i18n.t("pdf_corpus.builds", "Corpus builds") }}</b
            ><span>{{ buildsTotal }} {{ i18n.t("pdf_corpus.total", "total") }}</span>
          </div>
          <button
            type="button"
            class="icon-button"
            :title="i18n.t('pdf_corpus.refresh_builds', 'Refresh builds')"
            :aria-label="i18n.t('pdf_corpus.refresh_builds', 'Refresh builds')"
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
              >{{ build.record_count || 0 }} {{ i18n.t("pdf_corpus.records", "records") }} ·
              {{ formatDate(build.created_at) }}</small
            ></span
          >
        </button>
        <div v-if="!builds.length" class="rail-empty">
          {{ i18n.t("pdf_corpus.no_builds", "No builds yet.") }}
        </div>
      </aside>

      <main class="build-main">
        <section
          v-if="currentBuild"
          class="build-summary"
          :aria-labelledby="'pdf-corpus-current-build'"
        >
          <div v-if="!showReviewWorkspace || finishPhase" class="summary-top">
            <div>
              <span class="eyebrow">{{ currentBuild.profile_id }}</span>
              <h2 id="pdf-corpus-current-build">{{ currentBuild.source_filename }}</h2>
              <p>{{ currentBuild.build_id }}</p>
            </div>
            <div class="summary-actions">
              <button v-if="buildRunning" type="button" class="btn" @click="cancelBuild">
                {{ i18n.t("pdf_corpus.cancel", "Cancel") }}
              </button>
              <button
                v-if="canResume"
                type="button"
                class="btn"
                @click="resumeBuild"
                :disabled="busy !== ''"
              >
                {{ i18n.t("pdf_corpus.resume", "Resume from checkpoint") }}
              </button>
              <a
                v-if="currentBuild.publication"
                class="btn primary"
                :href="pdfCorpusApi.publicationUrl(currentBuild.publication.publication_id)"
                >{{ i18n.t("pdf_corpus.download_jsonl", "Download JSONL") }}</a
              >
            </div>
          </div>
          <CorpusBuildLifecycleCard
            v-if="!showReviewWorkspace || finishPhase"
            :build="currentBuild"
          />
          <CorpusQualitySummary
            v-if="!awaitingManifestReview && (!showReviewWorkspace || finishPhase)"
            :build="currentBuild"
          />

          <CorpusBuildStageNotice
            v-if="buildRunning && !hasRecordTopology"
            :stage="currentBuild.stage"
          />
          <CorpusFinishWorkspace
            v-if="!awaitingManifestReview && finishPhase"
            :build="currentBuild"
            :busy="busy !== ''"
            @retry-metadata="retryIncompleteMetadata"
            @review-metadata="openMetadataIssueQueue"
            @review-rejected="openRejectedQueue"
            @review-records="openAllReviewQueue"
            @review-source="openSourceIssueQueue"
            @restore-rejected="restoreAllRejected"
            @start-new="startNewBuildSetup"
            @edit-document-metadata="documentMetadataOpen = true"
            @rerun-enrichment="
              llmActionProviderId = selectedProviderId || providerProfiles[0]?.id || '';
              metadataEnrichmentOpen = true;
            "
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
            v-if="!awaitingManifestReview && (!showReviewWorkspace || finishPhase)"
            :build="currentBuild"
          />
          <details v-if="!showReviewWorkspace || finishPhase" class="technical-details">
            <summary>
              {{ i18n.t("pdf_corpus.technical_details", "Technical build details") }}
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
                {{ i18n.t("pdf_corpus.manifest_review_required", "Review document structure") }}
              </h3>
              <p>
                {{
                  i18n.t(
                    "pdf_corpus.manifest_review_required_help",
                    "Confirm the detected work-level metadata and printed-page mapping before DerridAI lets those values propagate into semantic segmentation and generated records.",
                  )
                }}
              </p>
            </div>
            <button
              type="button"
              class="btn primary"
              @click="confirmManifest"
              :disabled="busy !== '' || !contextSafe"
            >
              {{ i18n.t("pdf_corpus.confirm_manifest_continue", "Confirm document & continue") }}
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
                {{ i18n.t("pdf_corpus.retry_in_progress", "Retrying unresolved segmentation") }}
              </h3>
              <p>
                {{
                  i18n.t(
                    "pdf_corpus.retry_in_progress_help",
                    "DerridAI has resumed from the last safe checkpoint. The retry action is locked while this run is active; watch the stage and progress here or on Home.",
                  )
                }}
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
                {{ i18n.t("pdf_corpus.build_stopped_title", "Build stopped before completion") }}
              </h3>
              <p>
                {{
                  currentBuild.error ||
                  i18n.t(
                    "pdf_corpus.build_stopped_help",
                    "Completed checkpoints were preserved. Review the provider and execution settings above, then resume from the last safe checkpoint.",
                  )
                }}
              </p>
              <small>{{
                i18n.t(
                  "pdf_corpus.build_stopped_checkpoint",
                  "Resuming does not restart completed stages or discard validated records.",
                )
              }}</small>
            </div>
          </section>
          <section
            v-if="segmentationNeedsReview && (!showReviewWorkspace || finishPhase)"
            class="segmentation-blocked segmentation-review-localized"
            role="status"
            aria-labelledby="segmentation-review-title"
          >
            <div>
              <h3 id="segmentation-review-title">
                {{
                  i18n.t("pdf_corpus.segmentation_review_title", "Localized segmentation review")
                }}
              </h3>
              <p>
                {{
                  i18n.t(
                    "pdf_corpus.segmentation_review_help",
                    "The corpus was constructed successfully. A small number of boundary decisions may still need review; these are boundary-level questions and do not mark the neighboring records as failed. Metadata enrichment continues normally.",
                  )
                }}
              </p>
            </div>
            <details v-if="currentBuild.segmentation_unresolved_regions?.length">
              <summary>
                {{
                  i18n.tf("pdf_corpus.unresolved_count", "{count} boundary decision(s) to review", {
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
              (!showReviewWorkspace || finishPhase)
            "
            class="manifest-details"
            :open="awaitingManifestReview"
          >
            <summary>
              {{ i18n.t("pdf_corpus.document_manifest", "Document manifest") }} ·
              {{ i18n.t("pdf_corpus.revision", "revision") }}
              {{ currentBuild.manifest_revision || 1 }}
            </summary>
            <DocumentManifestEditor
              :manifest="currentBuild.manifest || {}"
              :disabled="buildRunning || busy !== ''"
              @save="saveManifest"
              @reanalyze="reanalyzeDocument"
            />
          </details>
          <div v-if="!showReviewWorkspace || finishPhase" class="provenance-strip">
            <span>SHA {{ currentBuild.source_sha256?.slice(0, 12) }}…</span
            ><span>{{
              currentBuild.model ||
              selectedProfileModel ||
              i18n.t("pdf_corpus.provider_default", "Provider default")
            }}</span
            ><span
              >{{ i18n.t("schemas.version", "Schema version") }} v{{
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
              llmActionProviderId = selectedProviderId || providerProfiles[0]?.id || '';
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
            <section
              class="review-toolbar"
              :aria-label="i18n.t('pdf_corpus.review_controls', 'Record review controls')"
            >
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
                i18n.t("pdf_corpus.search_records", "Search generated records")
              }}</label
              ><input
                id="pdf-corpus-record-search"
                v-model="recordQuery"
                class="control"
                :placeholder="i18n.t('pdf_corpus.search_records', 'Search generated records')"
              />
              <div
                class="workspace-switcher"
                role="group"
                :aria-label="i18n.t('pdf_corpus.review_workspace', 'Review workspace')"
              >
                <button
                  type="button"
                  class="btn small"
                  :aria-pressed="reviewWorkspaceMode === 'record'"
                  @click="setReviewWorkspaceMode('record')"
                >
                  {{ i18n.t("pdf_corpus.workspace.record", "Record") }}</button
                ><button
                  type="button"
                  class="btn small"
                  :aria-pressed="reviewWorkspaceMode === 'metadata'"
                  :aria-label="i18n.t('pdf_corpus.workspace.metadata', 'Metadata workspace')"
                  :disabled="!selectedRecord"
                  @click="setReviewWorkspaceMode('metadata')"
                >
                  {{ i18n.t("pdf_corpus.workspace.metadata_short", "Metadata") }}</button
                ><button
                  type="button"
                  class="btn small"
                  :aria-pressed="reviewWorkspaceMode === 'source'"
                  :aria-label="i18n.t('pdf_corpus.workspace.source', 'Source workspace')"
                  :disabled="!selectedRecord"
                  @click="setReviewWorkspaceMode('source')"
                >
                  {{ i18n.t("pdf_corpus.workspace.source_short", "Source") }}
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
                    i18n.tf("pdf_corpus.accept_clean", "Accept clean ({count})", {
                      count: readyCount,
                    })
                  }}</button
                ><CorpusActionMenu
                  :label="i18n.t('pdf_corpus.bulk_actions', 'Bulk actions')"
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
                  {{ i18n.t("ui.previous", "Previous") }}</button
                ><span>{{ pageNumber }} / {{ pageCount }}</span
                ><button
                  type="button"
                  class="btn small"
                  @click="nextPage"
                  :disabled="recordOffset + pageSize >= recordTotal"
                >
                  {{ i18n.t("ui.next", "Next") }}
                </button>
              </div>
            </section>

            <section
              ref="reviewGridEl"
              class="review-grid record-first-review"
              :style="{
                '--rw-queue': `${queueSplitter.size.value}px`,
                '--rw-inspector': `${inspectorSplitter.size.value}px`,
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
                  <b id="pdf-corpus-records-pane">{{
                    i18n.t("pdf_corpus.review_queue", "Review queue")
                  }}</b
                  ><button
                    type="button"
                    class="link-button queue-toggle"
                    @click="reviewQueueCollapsed = true"
                  >
                    {{ i18n.t("pdf_corpus.hide_queue", "Hide queue") }}</button
                  ><label class="select-visible"
                    ><input
                      type="checkbox"
                      :checked="allVisibleSelected"
                      :disabled="!records.length || busy !== ''"
                      @change="toggleVisibleSelection(($event.target as HTMLInputElement).checked)"
                    /><span>{{
                      i18n.t("pdf_corpus.select_visible", "Select visible")
                    }}</span></label
                  ><span>{{ recordTotal }}</span>
                </div>
                <div v-for="record in records" :key="record.record_id" class="record-row-wrap">
                  <label class="record-select"
                    ><input
                      type="checkbox"
                      :checked="selectedReviewIds.has(record.record_id)"
                      :aria-label="
                        i18n.tf('pdf_corpus.select_record_id', 'Select {record}', {
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
                      i18n.tf("pdf_corpus.select_record_id", "Select {record}", {
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
                        >{{ i18n.t("pdf_corpus.pages", "pp.") }} {{ record.page_start }}–{{
                          record.page_end
                        }}
                        · {{ record.text_length.toLocaleString() }}
                        {{ i18n.t("pdf_corpus.characters", "chars") }}</small
                      ><span class="record-row-status" :data-state="recordState(record)">{{
                        recordStateLabel(record)
                      }}</span
                      ><small v-if="extraIssueKinds(record).length" class="record-issue-summary">{{
                        extraIssueKinds(record)
                          .map((kind) => i18n.t(`pdf_corpus.record_state.${kind}`, kind))
                          .join(" · ")
                      }}</small></span
                    >
                  </button>
                </div>
                <div v-if="recordsLoading && !reviewHydrated" class="rail-empty" role="status">
                  {{ i18n.t("pdf_corpus.loading_records", "Loading generated records…") }}
                </div>
                <div v-else-if="!records.length" class="rail-empty">
                  {{ i18n.t("pdf_corpus.no_records_filter", "No records match this queue.") }}
                  <button
                    type="button"
                    class="btn small"
                    @click="
                      reviewQueue = 'all';
                      recordQuery = '';
                    "
                  >
                    {{ i18n.t("pdf_corpus.show_all_records", "Show all records") }}
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
                :aria-label="i18n.t('pdf_corpus.resize_queue', 'Resize review queue')"
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
                        {{ i18n.t("pdf_corpus.show_queue", "Show queue") }}</button
                      ><span class="eyebrow">{{
                        i18n.t("pdf_corpus.proposed_record", "Proposed record")
                      }}</span>
                      <h3 id="review-record-title">{{ selectedRecord.record_id }}</h3>
                      <p>
                        {{ i18n.t("pdf_corpus.pages", "pp.") }} {{ selectedRecord.page_start }}–{{
                          selectedRecord.page_end
                        }}
                        · {{ selectedRecord.text_length.toLocaleString() }}
                        {{ i18n.t("pdf_corpus.characters", "chars")
                        }}{{ selectedRecordActivitySummary }}
                      </p>
                    </div>
                    <div class="record-head-actions">
                      <div
                        class="decision-history"
                        role="group"
                        :aria-label="i18n.t('pdf_corpus.record_history', 'Review history')"
                      >
                        <button
                          type="button"
                          class="btn small"
                          @click="undoReview"
                          :disabled="busy !== ''"
                        >
                          <AppIcon name="history" /><span class="btn-text">{{
                            i18n.t("pdf_corpus.undo", "Undo")
                          }}</span></button
                        ><button
                          type="button"
                          class="btn small"
                          @click="redoReview"
                          :disabled="busy !== ''"
                        >
                          <AppIcon name="history" class="flip-inline" /><span class="btn-text">{{
                            i18n.t("pdf_corpus.redo", "Redo")
                          }}</span>
                        </button>
                      </div>
                      <button type="button" class="btn small" @click="openFocusView">
                        {{ i18n.t("pdf_corpus.focus_view", "Focus view") }}
                      </button>
                    </div>
                  </header>
                  <CorpusSourceIssuePanel
                    v-if="selectedRecord.source_quality_issues?.length"
                    :issues="selectedRecord.source_quality_issues"
                    interactive
                    @edit-text="beginTextEdit"
                    @open-source="reviewInspectorTab = 'source'"
                  />
                  <aside
                    v-if="selectedRecord.text_touchup_proposal?.status === 'pending_review'"
                    class="review-reason touchup-review-notice"
                    role="status"
                  >
                    <b>{{
                      i18n.t(
                        "pdf_corpus.llm_touchup_proposal_available",
                        "LLM text touch-up proposal available",
                      )
                    }}</b
                    ><span>{{
                      i18n.t(
                        "pdf_corpus.llm_touchup_proposal_help",
                        "Review the proposed corrections before saving; the current reviewed text is unchanged.",
                      )
                    }}</span
                    ><button
                      type="button"
                      class="btn small"
                      @click="beginTextEdit(true)"
                      :disabled="busy !== '' || reviewLocked"
                    >
                      {{ i18n.t("pdf_corpus.review_touchup_proposal", "Review proposal") }}
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
                        : i18n.t("pdf_corpus.why_review", "Why review")
                    }}</b
                    ><span>{{ selectedRecord.review_reason }}</span>
                  </aside>
                  <section class="record-text-review" aria-labelledby="reviewed-record-text-title">
                    <header>
                      <div>
                        <b id="reviewed-record-text-title">{{
                          i18n.t("pdf_corpus.reviewed_record_text", "Reviewed record text")
                        }}</b
                        ><span
                          v-if="selectedRecord.text_review_status === 'human_corrected'"
                          class="human-corrected"
                          >{{ i18n.t("pdf_corpus.human_corrected", "Human corrected") }}</span
                        ><span
                          v-else-if="selectedRecord.text_review_status === 'human_reviewed'"
                          class="human-corrected"
                          >{{ i18n.t("pdf_corpus.human_reviewed", "Human reviewed") }}</span
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
                          {{ i18n.t("pdf_corpus.clean_text", "Clean text") }}</button
                        ><button
                          v-if="editingText"
                          type="button"
                          class="btn small"
                          @click="llmTouchupOpen = true"
                          :disabled="busy !== '' || reviewLocked"
                        >
                          {{ i18n.t("pdf_corpus.llm_touchup", "LLM touch-up") }}</button
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
                          {{ i18n.t("pdf_corpus.mark_text_reviewed", "Mark reviewed") }}</button
                        ><button
                          type="button"
                          class="btn small"
                          @click="editingText ? cancelTextEdit() : beginTextEdit()"
                          :disabled="busy !== '' || reviewLocked"
                        >
                          {{
                            editingText
                              ? i18n.t("ui.cancel", "Cancel")
                              : i18n.t("pdf_corpus.edit_text", "Edit text")
                          }}
                        </button>
                      </div>
                    </header>
                    <textarea
                      v-if="editingText"
                      v-model="textDraft"
                      class="record-text-editor"
                      :aria-label="
                        i18n.t('pdf_corpus.reviewed_record_text', 'Reviewed record text')
                      "
                    ></textarea>
                    <div v-else class="record-primary-text">{{ selectedRecord.text }}</div>
                    <div
                      v-if="editingText && selectedRecord.source_quality_issues?.length"
                      class="text-review-actions"
                    >
                      <label
                        v-if="selectedRecord.source_quality_issues?.length"
                        class="resolve-source-check"
                        ><input v-model="resolveSourceOnTextSave" type="checkbox" /><span>{{
                          i18n.t(
                            "pdf_corpus.resolve_source_with_correction",
                            "Mark this record-level source issue resolved by the reviewed correction",
                          )
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
                      <b>{{
                        i18n.t(
                          "pdf_corpus.metadata_decision_required",
                          "Metadata decision required",
                        )
                      }}</b>
                      {{
                        i18n.tf(
                          "pdf_corpus.resolve_metadata_before_accept_fields",
                          "Confirm {fields} before accepting this record.",
                          { fields: selectedMetadataBlockingLabel },
                        )
                      }}
                    </p>
                    <div
                      v-if="editingText"
                      class="decision-bar text-edit-bar"
                      role="group"
                      :aria-label="i18n.t('pdf_corpus.edit_text', 'Edit text')"
                    >
                      <span class="text-save-hint">{{
                        i18n.t(
                          "pdf_corpus.text_save_hint",
                          "Saving confirms that you reviewed this record text.",
                        )
                      }}</span>
                      <div class="decision-actions">
                        <button type="button" class="btn small" @click="cancelTextEdit">
                          {{ i18n.t("ui.cancel", "Cancel") }}
                        </button>
                        <button
                          type="button"
                          class="btn small primary"
                          @click="saveReviewedText()"
                          :disabled="busy !== '' || !textDraft.trim()"
                        >
                          {{
                            busy === "text"
                              ? i18n.t("ui.saving", "Saving…")
                              : i18n.t("pdf_corpus.save_and_mark_reviewed", "Save & mark reviewed")
                          }}
                        </button>
                      </div>
                    </div>
                    <div
                      v-else
                      class="decision-bar"
                      role="group"
                      :aria-label="i18n.t('pdf_corpus.record_decision', 'Record decision')"
                    >
                      <CorpusActionMenu
                        :label="i18n.t('pdf_corpus.more_actions', 'More actions')"
                        :menu-label="
                          i18n.t('pdf_corpus.more_record_actions', 'More record actions')
                        "
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
                          {{ i18n.t("pdf_corpus.skip", "Skip") }}
                        </button>
                        <button
                          type="button"
                          class="btn small danger"
                          @click="rejectRecord"
                          :disabled="busy !== ''"
                        >
                          {{ i18n.t("pdf_corpus.reject_next", "Reject & next") }}
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
                              ? i18n.t("pdf_corpus.reopen", "Reopen")
                              : i18n.t("pdf_corpus.accept_next", "Accept & next")
                          }}
                        </button>
                      </div>
                    </div>
                  </footer>
                </template>
                <div v-else class="inspector-empty">
                  {{
                    i18n.t(
                      "pdf_corpus.select_record",
                      "Select a generated record to inspect its source binding and metadata.",
                    )
                  }}
                </div>
              </article>

              <div
                v-if="reviewWorkspaceMode === 'record'"
                class="review-splitter"
                data-splitter="inspector"
                role="separator"
                tabindex="0"
                aria-orientation="vertical"
                :aria-label="i18n.t('pdf_corpus.resize_inspector', 'Resize review details')"
                v-bind="inspectorSplitter.aria()"
                @pointerdown="inspectorSplitter.onPointerDown"
                @keydown="inspectorSplitter.onKeydown"
                @dblclick="inspectorSplitter.reset"
              ></div>
              <aside
                ref="reviewInspectorEl"
                class="review-inspector"
                :aria-label="i18n.t('pdf_corpus.review_details', 'Review details')"
              >
                <div v-if="reviewWorkspaceMode !== 'record'" class="detail-workspace-head">
                  <div>
                    <span class="eyebrow">{{
                      i18n.t("pdf_corpus.review_workspace", "Review workspace")
                    }}</span>
                    <h3>
                      {{
                        reviewWorkspaceMode === "metadata"
                          ? i18n.t("pdf_corpus.workspace.metadata", "Metadata workspace")
                          : i18n.t("pdf_corpus.workspace.source", "Source workspace")
                      }}
                    </h3>
                    <p>
                      {{
                        reviewWorkspaceMode === "metadata"
                          ? i18n.t(
                              "pdf_corpus.workspace.metadata_help",
                              "Resolve attribution, discourse, and indexing metadata with evidence and provenance visible.",
                            )
                          : i18n.t(
                              "pdf_corpus.workspace.source_help",
                              "Inspect the source page, immutable extraction, boundary decisions, and transcription tools at full working width.",
                            )
                      }}
                    </p>
                  </div>
                  <button type="button" class="btn small" @click="setReviewWorkspaceMode('record')">
                    {{ i18n.t("pdf_corpus.workspace.back_record", "Back to record") }}
                  </button>
                </div>
                <div
                  v-show="reviewWorkspaceMode === 'record'"
                  class="review-inspector-tabs"
                  role="tablist"
                  :aria-label="i18n.t('pdf_corpus.review_detail_views', 'Review detail views')"
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
                    {{ i18n.t("pdf_corpus.metadata_tab", "Metadata")
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
                    {{ i18n.t("pdf_corpus.evidence_tab", "Evidence") }}
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
                    {{ i18n.t("pdf_corpus.source_tab", "Source") }}
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
                  <section v-if="currentBuild?.manifest" class="document-metadata-launch">
                    <div>
                      <b>{{
                        i18n.t(
                          "pdf_corpus.document_metadata_defaults",
                          "Document metadata defaults",
                        )
                      }}</b
                      ><span>{{
                        i18n.t(
                          "pdf_corpus.document_metadata_defaults_help",
                          "Edit inherited bibliographic defaults in a dedicated workspace. Record-level overrides remain untouched.",
                        )
                      }}</span>
                    </div>
                    <button
                      type="button"
                      class="btn"
                      :disabled="busy !== ''"
                      @click="documentMetadataOpen = true"
                    >
                      {{ i18n.t("pdf_corpus.edit_document_metadata", "Edit document metadata") }}
                    </button>
                  </section>
                  <details class="record-data">
                    <summary>
                      {{ i18n.t("pdf_corpus.advanced_metadata", "Advanced metadata") }}
                    </summary>
                    <p class="help">
                      {{
                        i18n.t(
                          "pdf_corpus.metadata_help",
                          "Typed controls above are preferred. This advanced editor is for supported interpretive metadata only; source-bound fields remain protected.",
                        )
                      }}
                    </p>
                    <LlmExecutionControl
                      :model-value="llmActionProviderId || selectedProviderId"
                      :model-override="llmActionModel"
                      :profiles="providerProfiles"
                      :disabled="busy !== ''"
                      :task="
                        i18n.t(
                          'pdf_corpus.metadata_rerun_provider_help',
                          'Rerun only this Record with the selected LLM profile. Existing human-confirmed values remain authoritative.',
                        )
                      "
                      @update:model-value="(value) => (llmActionProviderId = value)"
                      @update:model-override="(value) => (llmActionModel = value)"
                    /><label class="sr-only" for="pdf-corpus-metadata">{{
                      i18n.t("pdf_corpus.interpretive_metadata", "Interpretive metadata")
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
                        {{ i18n.t("pdf_corpus.save_metadata", "Save metadata") }}</button
                      ><label class="rerun-family"
                        ><span>{{ i18n.t("pdf_corpus.rerun_family", "Rerun family") }}</span
                        ><select v-model="metadataRerunFamily" class="control small">
                          <option value="all">
                            {{ i18n.t("pdf_corpus.metadata_family.all", "All metadata families") }}
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
                        :title="
                          i18n.t(
                            'pdf_corpus.rerun_metadata_help',
                            'Re-evaluate only this Record using the selected metadata family.',
                          )
                        "
                        @click="rerunMetadata()"
                        :disabled="busy !== ''"
                      >
                        {{ i18n.t("pdf_corpus.rerun_metadata", "Rerun this Record") }}</button
                      ><button
                        type="button"
                        class="btn small"
                        :title="
                          i18n.t(
                            'pdf_corpus.metadata_enrichment_again_help',
                            'Run a multi-Record enrichment pass with scope, family, and pass options.',
                          )
                        "
                        @click="
                          llmActionProviderId = selectedProviderId || providerProfiles[0]?.id || '';
                          metadataEnrichmentOpen = true;
                        "
                        :disabled="busy !== ''"
                      >
                        {{
                          i18n.t(
                            "pdf_corpus.metadata_enrichment_again",
                            "Run enrichment across Records",
                          )
                        }}
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
                    {{
                      i18n.t(
                        "pdf_corpus.evidence_review_help",
                        "Select a metadata field to inspect or adjust its source-block evidence.",
                      )
                    }}
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
                        ><span>PDF {{ block.page }} · {{ block.type }}</span>
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
                            ? i18n.t("pdf_corpus.remove_evidence", "Remove as evidence")
                            : i18n.t("pdf_corpus.add_evidence", "Add as evidence")
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
                      {{ i18n.t("pdf_corpus.boundary_second_reader", "Boundary second reader") }}
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
                      {{ i18n.t("pdf_corpus.extracted_source_text", "Immutable extracted source") }}
                    </summary>
                    <p class="inspector-help">
                      {{
                        i18n.t(
                          "pdf_corpus.extracted_source_text_help",
                          "This is the audit reference produced by PDF extraction. Human corrections change the reviewed record text, never these source blocks.",
                        )
                      }}
                    </p>
                    <pre
                      v-if="selectedRecord.source_extracted_text"
                      class="original-extraction-snapshot"
                      >{{ selectedRecord.source_extracted_text }}</pre>
                    <div class="source-blocks">
                      <article
                        v-for="(block, index) in visibleBlocks"
                        :key="block.block_id"
                        class="source-block"
                        :class="{ 'evidence-block': evidenceBlockIds.has(block.block_id) }"
                      >
                        <header>
                          <span>{{ block.block_id }}</span
                          ><span>PDF {{ block.page }} · {{ block.type }}</span>
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
                              ? i18n.t("pdf_corpus.remove_evidence", "Remove as evidence")
                              : i18n.t("pdf_corpus.add_evidence", "Add as evidence")
                          }}
                          · {{ selectedEvidenceField }}</button
                        ><button
                          v-if="index < visibleBlocks.length - 1"
                          type="button"
                          class="split-button"
                          @click="split(block.block_id)"
                          :disabled="busy !== ''"
                        >
                          {{ i18n.t("pdf_corpus.split_after", "Split after this block") }}
                        </button>
                      </article>
                    </div>
                  </details>
                  <details class="source-tool-section">
                    <summary>
                      {{ i18n.t("pdf_corpus.revision_history", "Revision history") }}
                    </summary>
                    <CorpusRevisionHistory :record="selectedRecord" />
                  </details>
                </section>
                <div v-else class="inspector-empty">
                  {{
                    i18n.t(
                      "pdf_corpus.select_record",
                      "Select a generated record to inspect its source binding and metadata.",
                    )
                  }}
                </div>
              </aside>
            </section>
          </div>
        </template>

        <section v-else class="builder-empty">
          <h2>{{ i18n.t("pdf_corpus.no_selected_build", "No corpus build selected") }}</h2>
          <p>
            {{
              i18n.t(
                "pdf_corpus.no_selected_build_help",
                "Persist a PDF source and start a semantic corpus build, or choose a historical build from the rail.",
              )
            }}
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
          setMessage(
            i18n.t(
              'pdf_corpus.cleanup_applied_draft',
              'Cleanup applied to the reviewed-text draft. Save to persist it.',
            ),
          );
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
              providerProfiles.find((p) => p.id === llmActionProviderId)?.max_concurrent_requests ||
                1,
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
    <UiDialog
      v-if="schemaEditorOpen"
      size="xlarge"
      :title="i18n.t('schemas.manage_title', 'Metadata schemas')"
      :description="
        i18n.t(
          'schemas.manage_help',
          'Define the fields on JSONL records, their allowed values and the instructions the model is given. Changing a schema does not change builds already made.',
        )
      "
      :close-label="i18n.t('ui.close', 'Close')"
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
    </UiDialog>
    <UiDialog
      v-if="handsFreeOpen"
      size="medium"
      :title="i18n.t('pdf_corpus.run_hands_free_title', 'Run hands-free')"
      :description="
        i18n.t(
          'pdf_corpus.run_hands_free_help',
          'Settle this build with the rules below, without reviewing each record.',
        )
      "
      :close-label="i18n.t('ui.close', 'Close')"
      @close="handsFreeOpen = false"
    >
      <CorpusHandsFreeSettings v-model="handsFree" :disabled="busy !== ''" :show-enable="false" />
      <template #footer
        ><button type="button" class="btn" @click="handsFreeOpen = false">
          {{ i18n.t("ui.cancel", "Cancel") }}</button
        ><button type="button" class="btn primary" :disabled="busy !== ''" @click="runHandsFree">
          {{ i18n.t("pdf_corpus.run_hands_free_action", "Run hands-free") }}
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
        :source-blocks="visibleBlocks"
        :busy="busy !== '' || reviewLocked"
        :can-merge-previous="canMergePrevious"
        :can-merge-next="canMergeNext"
        :can-accept="
          !selectedMetadataBlocked && !Boolean(selectedRecord.source_quality_issues?.length)
        "
        :region-types="regionTypes"
        :discourse-roles="discourseRoles"
        :recurring-lines="recurringCleanupLines"
        :document-terms="cleanupDocumentTerms"
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
        @close="focusView = false"
        @history-back="focusHistoryMove(-1)"
        @history-forward="focusHistoryMove(1)"
        @previous-record="focusQueueMove(-1)"
        @next-record="focusQueueMove(1)"
        @requeue-metadata="requeueCurrentRecord"
        @save-text="saveTextFromFocus"
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
    /></Teleport>
  </section>
</template>

<style scoped>
.corpus-builder {
  padding: 20px 22px 32px;
  display: grid;
  gap: 14px;
}
.builder-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-end;
}
.builder-header h1 {
  font-size: 1.625rem;
  margin: 3px 0 6px;
}
.builder-header p {
  margin: 0;
  max-width: 850px;
  color: var(--muted);
  line-height: 1.5;
}
.eyebrow {
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--muted);
  font-weight: 700;
}
.header-actions,
.summary-actions,
.inspector-actions,
.pager {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.status-region:focus {
  outline: none;
}
.builder-message {
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
  font-size: 0.8125rem;
}
.builder-message.error,
.build-warning {
  border-color: var(--tone-danger-border);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.builder-setup {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(420px, 1.35fr);
  gap: 12px;
  align-items: start;
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 14px;
  padding: 14px;
}
.setup-card {
  min-width: 0;
  height: 100%;
  display: grid;
  align-content: start;
  gap: 8px;
  padding: 13px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: linear-gradient(180deg, var(--card), var(--card));
}
.setup-source,
.provider-area {
  display: grid;
  gap: 8px;
}
.setup-card-heading {
  display: grid;
  gap: 3px;
}
.setup-card-heading b {
  font-size: 0.8125rem;
}
.setup-card-heading small {
  font-size: 0.8125rem !important;
  line-height: 1.45;
}
.builder-setup label {
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--muted);
}
.builder-setup small {
  font-size: 0.8125rem;
  color: var(--muted);
}
.execution-config,
.advanced-config,
.build-launch-row {
  grid-column: 1/-1;
}
.advanced-config {
  grid-column: 1/-1;
}
.advanced-config summary {
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 700;
}
.escalation-field {
  display: grid;
  grid-template-columns: minmax(150px, 0.7fr) minmax(220px, 1fr);
  gap: 12px;
  align-items: center;
  padding: 10px 11px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.escalation-field > span {
  display: grid;
  gap: 2px;
}
.escalation-field b {
  font-size: 0.8125rem;
}
.escalation-field small {
  font-size: 0.8125rem;
  line-height: 1.4;
  color: var(--muted);
}
.advanced-grid {
  display: grid;
  grid-template-columns: max-content 1fr max-content 1fr;
  gap: 8px 10px;
  margin-top: 8px;
  align-items: center;
}
.build-launch-row {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(280px, 1.2fr) auto;
  gap: 12px;
  align-items: center;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--soft);
}
.launch-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.launch-copy b {
  font-size: 0.8125rem;
}
.launch-copy span {
  font-size: 0.8125rem;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.build-button {
  min-height: 38px;
  padding-inline: 17px;
}
.context-blocker {
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
}
.builder-workspace {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  min-height: 720px;
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  background: var(--card);
}
.build-rail {
  border-inline-end: 1px solid var(--line);
  background: var(--soft);
  padding: 10px;
  overflow: auto;
}
.rail-title,
.pane-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.rail-title {
  padding: 6px 4px 10px;
}
.rail-title > div {
  display: grid;
}
.rail-title b,
.pane-head b {
  font-size: 0.8125rem;
}
.rail-title span,
.pane-head span {
  font-size: 0.8125rem;
  color: var(--muted);
}
.icon-button {
  border: 0;
  background: transparent;
  cursor: pointer;
  font-size: 1.125rem;
}
.build-row {
  width: 100%;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 10px;
  padding: 9px;
  display: grid;
  grid-template-columns: 10px 1fr;
  gap: 9px;
  text-align: start;
  cursor: pointer;
}
.build-row:hover,
.build-row.active {
  background: var(--card);
  border-color: var(--line);
}
.build-row span:last-child {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.build-row b {
  font-size: 0.8125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.build-row small {
  font-size: 0.8125rem;
  color: var(--muted);
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #777;
  margin-top: 3px;
}
.status-dot[data-status="ready"],
.status-dot[data-status="published"] {
  background: #287a4c;
}
.status-dot[data-status="running"],
.status-dot[data-status="queued"] {
  background: #8e6815;
}
.status-dot[data-status="failed"],
.status-dot[data-status="interrupted"] {
  background: #a13f3f;
}
.build-main {
  min-width: 0;
  display: grid;
  align-content: start;
}
.build-summary {
  padding: 15px 16px;
  border-bottom: 1px solid var(--line);
  display: grid;
  gap: 10px;
}
.summary-top {
  display: flex;
  justify-content: space-between;
  gap: 18px;
}
.summary-top h2 {
  margin: 2px 0;
  font-size: 1.125rem;
}
.summary-top p {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--muted);
}
.build-status-line,
.provenance-strip,
.validation-strip {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.8125rem;
  color: var(--muted);
}
.pill {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 7px;
  text-transform: uppercase;
  font-weight: 800;
  letter-spacing: 0.04em;
}
.progress-track {
  height: 7px;
  border-radius: 999px;
  background: var(--soft);
  overflow: hidden;
}
.progress-track span {
  display: block;
  height: 100%;
  background: var(--accent);
  transition: width 0.25s;
}
.provenance-strip code {
  font-size: 0.8125rem;
}
.manifest-details {
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 8px 10px;
}
.manifest-details > summary {
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 800;
}
.build-warning {
  display: grid;
  gap: 3px;
  padding: 9px;
  border: 1px solid;
  border-radius: 8px;
  font-size: 0.8125rem;
}
.warnings {
  font-size: 0.8125rem;
}
.warnings summary {
  cursor: pointer;
  font-weight: 700;
}
.validation-strip {
  padding: 7px 9px;
  border-radius: 8px;
  background: var(--tone-ok-bg);
}
.validation-strip.invalid {
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.provider-model-summary {
  margin: 6px 0 0;
  font-size: 0.8125rem;
  color: var(--muted);
}
.provider-model-summary code {
  font-size: 0.8125rem;
  color: var(--text);
}
.review-handoff {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 11px 13px;
  border-bottom: 1px solid var(--line);
  background: var(--soft);
}
.review-handoff > div {
  display: grid;
  gap: 2px;
}
.review-handoff b {
  font-size: 0.8125rem;
}
.review-handoff span {
  font-size: 0.8125rem;
  color: var(--muted);
  line-height: 1.4;
}
.review-handoff > strong {
  white-space: nowrap;
  font-size: 0.8125rem;
}
.review-handoff[data-state="published"] {
  background: var(--tone-ok-bg);
}
.review-toolbar {
  display: grid;
  grid-template-columns: auto minmax(180px, 1fr) auto auto auto;
  gap: 10px;
  align-items: center;
  padding: 9px 12px;
  border-bottom: 1px solid var(--line);
  font-size: 0.8125rem;
}
.check {
  display: flex;
  gap: 6px;
  align-items: center;
}
.bulk-metadata-workspace {
  grid-column: 1/-1;
  margin: 0 10px 10px;
}
.review-bulk {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.danger {
  border-color: var(--tone-danger-border) !important;
  color: var(--tone-danger-fg) !important;
}
.review-grid {
  display: grid;
  grid-template-columns: minmax(360px, 1.2fr) minmax(240px, 0.65fr) minmax(300px, 0.85fr);
  min-height: 650px;
}
.source-pane,
.records-pane,
.inspector-pane {
  min-width: 0;
  overflow: auto;
  max-height: 76vh;
}
.source-pane,
.records-pane {
  border-inline-end: 1px solid var(--line);
}
.pane-head {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--card);
  padding: 9px 11px;
  border-bottom: 1px solid var(--line);
}
.source-page-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid var(--line);
  font-size: 0.8125rem;
  color: var(--muted);
}
.source-blocks {
  display: grid;
  gap: 8px;
  padding: 10px;
}
.source-block {
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 9px;
  position: relative;
}
.source-block.evidence-block {
  box-shadow: inset 3px 0 0 var(--accent);
}
[dir="rtl"] .source-block.evidence-block {
  box-shadow: inset -3px 0 0 var(--accent);
}
.source-block header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--muted);
}
.source-block p {
  white-space: pre-wrap;
  font:
    13px/1.52 Georgia,
    serif;
  margin: 7px 0;
}
.split-button {
  display: block;
  width: 100%;
  border: 0;
  border-top: 1px dashed var(--line);
  background: transparent;
  color: var(--muted);
  font-size: 0.8125rem;
  padding: 5px;
  cursor: pointer;
}
.evidence-toggle {
  display: block;
  width: 100%;
  margin: 5px 0;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--soft);
  color: var(--text);
  font-size: 0.8125rem;
  padding: 6px;
  text-align: start;
  cursor: pointer;
}
.evidence-toggle[aria-pressed="true"] {
  border-color: var(--accent);
  box-shadow: inset 3px 0 0 var(--accent);
}
.record-row {
  width: 100%;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  padding: 10px;
  display: grid;
  grid-template-columns: 10px 1fr;
  gap: 8px;
  text-align: start;
  cursor: pointer;
}
.record-row:hover,
.record-row.active {
  background: var(--soft);
}
.record-row span:last-child {
  display: grid;
  gap: 3px;
}
.record-row b {
  font-size: 0.8125rem;
}
.record-row small {
  font-size: 0.8125rem;
  color: var(--muted);
}
.inspector-pane details {
  border-bottom: 1px solid var(--line);
  padding: 10px 12px;
}
.inspector-pane summary {
  font-size: 0.8125rem;
  font-weight: 800;
  cursor: pointer;
}
.inspector-actions {
  padding: 9px 11px;
  border-bottom: 1px solid var(--line);
}
.record-text {
  white-space: pre-wrap;
  font:
    13px/1.55 Georgia,
    serif;
  margin-top: 9px;
}
.metadata-json {
  width: 100%;
  min-height: 230px;
  resize: vertical;
  font:
    12px/1.5 ui-monospace,
    SFMono-Regular,
    Menlo,
    monospace;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px;
  background: var(--bg);
  color: var(--text);
  margin: 7px 0;
}
.help {
  font-size: 0.8125rem;
  color: var(--muted);
  line-height: 1.45;
}
.evidence-list {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}
.evidence-list button {
  display: grid;
  gap: 2px;
  padding: 7px;
  background: var(--soft);
  border: 1px solid transparent;
  border-radius: 7px;
  text-align: start;
  color: inherit;
  cursor: pointer;
}
.evidence-list button.active {
  border-color: var(--accent);
}
.evidence-list b {
  font-size: 0.8125rem;
}
.evidence-list span,
.evidence-list small {
  font-size: 0.8125rem;
  color: var(--muted);
}
.rail-empty,
.inspector-empty,
.builder-empty {
  padding: 26px 14px;
  color: var(--muted);
  font-size: 0.8125rem;
}
.builder-empty {
  min-height: 420px;
  display: grid;
  place-content: center;
  text-align: center;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.btn:focus-visible,
.control:focus-visible,
.build-row:focus-visible,
.record-row:focus-visible,
.icon-button:focus-visible,
.split-button:focus-visible,
.evidence-toggle:focus-visible,
.evidence-list button:focus-visible,
summary:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.build-guidance {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.build-guidance .guidance-icon {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  font-weight: 850;
}
.build-guidance h3 {
  margin: 0 0 3px;
  font-size: 0.8125rem;
}
.build-guidance p {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.build-guidance small {
  display: block;
  margin-top: 4px;
  font-size: 0.8125rem;
  color: inherit;
  opacity: 0.8;
}
.running-guidance {
  background: var(--accent-soft, #eef6f2);
  border-color: var(--accent-soft-2, #dce9e3);
}
.running-guidance .guidance-icon {
  background: var(--card);
  color: var(--accent-fg);
}
.failure-guidance {
  background: var(--tone-danger-bg);
  border-color: var(--tone-danger-edge);
  color: var(--tone-danger-fg);
}
.failure-guidance .guidance-icon {
  background: var(--card);
  color: var(--tone-danger-fg);
}
.manifest-gate {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.manifest-gate h3 {
  margin: 0 0 4px;
  font-size: 0.8125rem;
}
.manifest-gate p {
  margin: 0;
  max-width: 800px;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.segmentation-blocked {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
  padding: 12px;
  border: 1px solid var(--tone-danger-border);
  border-radius: 10px;
  background: var(--tone-danger-bg);
}
.segmentation-blocked h3 {
  margin: 0 0 4px;
  font-size: 0.8125rem;
}
.segmentation-blocked p {
  margin: 0;
  max-width: 800px;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.segmentation-blocked details {
  grid-column: 1/-1;
  font-size: 0.8125rem;
}
.segmentation-blocked ul {
  margin: 6px 0 0;
  padding-inline-start: 20px;
}
.segmentation-blocked code {
  font-size: 0.8125rem;
}
.segmentation-review-localized {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
@media (prefers-reduced-motion: reduce) {
  .progress-track span {
    transition: none;
  }
}
@media (max-width: 1250px) {
  .review-grid {
    grid-template-columns: 1fr 0.72fr;
  }
  .inspector-pane {
    grid-column: 1/-1;
    border-top: 1px solid var(--line);
    max-height: none;
  }
  .source-pane,
  .records-pane {
    max-height: 65vh;
  }
}
@media (max-width: 900px) {
  .manifest-gate,
  .segmentation-blocked {
    grid-template-columns: 1fr;
  }
  .builder-header {
    align-items: flex-start;
    flex-direction: column;
  }
  .builder-setup {
    grid-template-columns: 1fr;
  }
  .build-launch-row {
    grid-template-columns: 1fr;
  }
  .escalation-field {
    grid-template-columns: 1fr;
  }
  .advanced-grid {
    grid-template-columns: 1fr;
  }
  .advanced-config {
    grid-column: auto;
  }
  .builder-workspace {
    grid-template-columns: 1fr;
  }
  .build-rail {
    border-inline-end: 0;
    border-bottom: 1px solid var(--line);
    max-height: 220px;
  }
  .review-toolbar {
    grid-template-columns: 1fr 1fr;
  }
  .review-grid {
    grid-template-columns: 1fr;
  }
  .source-pane,
  .records-pane {
    border-inline-end: 0;
    border-bottom: 1px solid var(--line);
    max-height: none;
  }
}

.active-build-settings {
  margin: 10px 0;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
}
.active-build-settings > summary {
  padding: 10px 12px;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 800;
}
.active-build-settings > div {
  display: flex;
  gap: 14px;
  align-items: center;
  flex-wrap: wrap;
  padding: 10px 12px;
  border-top: 1px solid var(--line);
  font-size: 0.8125rem;
  color: var(--muted);
}
.technical-details {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  overflow: hidden;
}
.technical-details > summary {
  padding: 9px 11px;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 800;
}
.technical-details > div,
.technical-details > section {
  border-top: 1px solid var(--line);
}
.review-toolbar {
  grid-template-columns: minmax(0, 1fr) minmax(220px, 0.7fr) auto auto;
}
.record-first-review {
  grid-template-columns: minmax(220px, 0.52fr) minmax(500px, 1.45fr) minmax(360px, 0.9fr);
}
.record-first-review > .records-pane {
  border-inline-end: 1px solid var(--line);
}
.record-first-review > .source-pane {
  border-inline-start: 1px solid var(--line);
  border-inline-end: 0;
}
.record-review-pane {
  min-width: 0;
  max-height: 76vh;
  overflow: auto;
  background: var(--card);
}
.record-review-head {
  position: sticky;
  top: 0;
  z-index: 4;
  background: var(--card);
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
}
.record-review-head h3 {
  margin: 2px 0;
  font-size: 0.9375rem;
}
.record-review-head p {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--muted);
}
.record-primary-text {
  max-width: 80ch;
  margin: 0 auto;
  padding: 28px 32px;
  white-space: pre-wrap;
  font:
    17px/1.72 Georgia,
    serif;
}
.review-reason {
  display: grid;
  gap: 3px;
  margin: 12px 16px 0;
  padding: 10px 12px;
  border-radius: 9px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
}
.metadata-accept-blocker {
  margin: 0;
  padding: 9px 12px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 8px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
}
.decision-bar {
  position: sticky;
  bottom: 0;
  z-index: 4;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-top: 1px solid var(--line);
  background: color-mix(in srgb, var(--card) 96%, transparent);
  backdrop-filter: blur(6px);
}
.decision-actions,
.data-actions {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}
.record-data {
  border-top: 1px solid var(--line);
  padding: 10px 14px;
}
.record-data > summary,
.source-text-details > summary {
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 800;
}
.source-text-details {
  border-top: 1px solid var(--line);
  padding: 8px;
}
.source-pane,
.records-pane {
  max-height: 76vh;
  overflow: auto;
}
.source-pane .pdf-evidence-viewer {
  max-width: 100%;
}
@media (max-width: 1400px) {
  .record-first-review {
    grid-template-columns: minmax(210px, 0.5fr) minmax(460px, 1.35fr) minmax(320px, 0.8fr);
  }
  .record-primary-text {
    font-size: 1rem;
    padding: 24px;
  }
}
@media (max-width: 1100px) {
  .review-toolbar {
    grid-template-columns: 1fr 1fr;
  }
  .record-first-review {
    grid-template-columns: minmax(210px, 0.5fr) minmax(0, 1.5fr);
  }
  .record-first-review > .source-pane {
    grid-column: 1/-1;
    border-inline-start: 0;
    border-top: 1px solid var(--line);
    max-height: none;
  }
  .record-review-pane,
  .records-pane {
    max-height: 68vh;
  }
}
@media (max-width: 760px) {
  .review-toolbar {
    grid-template-columns: 1fr;
  }
  .record-first-review {
    grid-template-columns: 1fr;
  }
  .record-first-review > .records-pane {
    max-height: 260px;
    border-inline-end: 0;
    border-bottom: 1px solid var(--line);
  }
  .record-review-pane {
    max-height: none;
  }
  .metadata-accept-blocker {
    margin: 0;
    padding: 9px 12px;
    border: 1px solid var(--tone-warn-edge);
    border-radius: 8px;
    background: var(--tone-warn-bg);
    color: var(--tone-warn-fg);
    font-size: 0.8125rem;
  }
  .decision-bar {
    position: static;
    align-items: stretch;
    flex-direction: column;
  }
  .record-primary-text {
    font-size: 1rem;
    padding: 20px 18px;
  }
}
.review-stage-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 0.9fr);
  gap: 14px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.review-stage-summary > div {
  display: grid;
  gap: 3px;
}
.review-stage-summary b {
  font-size: 0.8125rem;
}
.review-stage-summary > span {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--muted);
}
.record-first-review {
  grid-template-columns: minmax(205px, 0.48fr) minmax(520px, 1.5fr) minmax(360px, 0.95fr);
}
.record-first-review > .records-pane {
  border-inline-end: 1px solid var(--line);
}
.record-review-pane,
.review-inspector,
.records-pane {
  min-width: 0;
  max-height: 76vh;
  overflow: auto;
}
.review-inspector {
  border-inline-start: 1px solid var(--line);
  background: var(--soft);
}
.review-inspector-tabs {
  position: sticky;
  top: 0;
  z-index: 6;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  background: var(--card);
  border-bottom: 1px solid var(--line);
}
.review-inspector-tabs button {
  min-height: 42px;
  border: 0;
  border-inline-end: 1px solid var(--line);
  background: transparent;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 800;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
}
.review-inspector-tabs button[aria-selected="true"] {
  background: var(--soft);
  color: var(--text);
  box-shadow: inset 0 -3px 0 var(--accent);
}
.review-inspector-tabs button span {
  min-width: 18px;
  border-radius: 999px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  padding: 1px 5px;
  font-size: 0.8125rem;
}
.review-inspector-panel {
  min-width: 0;
}
.review-inspector-panel > .resolution-panel {
  border-top: 0;
  background: transparent;
}
.review-inspector-panel .record-data {
  border-top: 1px solid var(--line);
  padding: 10px 12px;
  background: var(--card);
}
.inspector-help {
  margin: 0;
  padding: 12px 14px 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--muted);
}
.compact-source-blocks {
  padding-top: 6px;
}
.source-review-panel {
  background: var(--card);
  min-height: 100%;
}
.source-inspector-head {
  position: static;
  z-index: auto;
}
.metadata-row-warning {
  color: var(--tone-warn-fg) !important;
  font-weight: 800;
}
.metadata-accept-blocker {
  display: block;
}
.metadata-accept-blocker b {
  margin-inline-end: 4px;
}
.record-primary-text {
  max-width: 76ch;
}
.decision-bar {
  min-height: 56px;
}
.review-toolbar {
  grid-template-columns: minmax(0, 1fr) minmax(210px, 0.7fr) auto auto;
}
.review-bulk .btn {
  min-height: 34px;
}
@media (max-width: 1300px) {
  .record-first-review {
    grid-template-columns: minmax(200px, 0.48fr) minmax(460px, 1.4fr) minmax(330px, 0.9fr);
  }
}
@media (max-width: 1050px) {
  .record-first-review {
    grid-template-columns: minmax(200px, 0.48fr) minmax(0, 1.5fr);
  }
  .review-inspector {
    grid-column: 1/-1;
    border-inline-start: 0;
    border-top: 1px solid var(--line);
    max-height: 60vh;
  }
  .review-stage-summary {
    grid-template-columns: 1fr;
  }
  .review-toolbar {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 760px) {
  .record-first-review {
    grid-template-columns: 1fr;
  }
  .review-inspector {
    max-height: none;
  }
  .review-toolbar {
    grid-template-columns: 1fr;
  }
  .review-stage-summary {
    grid-template-columns: 1fr;
  }
  .review-inspector-tabs {
    top: 0;
  }
}

/* 0.48.1 Gifted Grungus — editable reviewed text, selective enrichment, explicit ownership, and concurrent-build clarity. */
.review-readonly-banner {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 10px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.review-readonly-banner > div {
  display: grid;
  gap: 3px;
}
.review-readonly-banner b {
  font-size: 0.8125rem;
}
.review-readonly-banner span {
  font-size: 0.8125rem;
  line-height: 1.45;
}
.builder-workspace.review-mode {
  grid-template-columns: minmax(0, 1fr);
}
.builder-workspace.review-mode .build-main {
  max-width: none;
  width: 100%;
}
.review-toolbar {
  position: sticky;
  top: 66px;
  z-index: 11;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 320px) auto;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.review-toolbar .control {
  min-height: 40px;
  font-size: 0.8125rem;
}
.review-bulk {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.pager {
  grid-column: 1/-1;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--muted);
}
.record-first-review {
  display: grid;
  grid-template-columns: minmax(220px, 260px) minmax(560px, 1.8fr) minmax(340px, 0.9fr);
  min-height: 620px;
  height: calc(100vh - 235px);
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  background: var(--card);
}
.records-pane,
.record-review-pane,
.review-inspector {
  max-height: none;
  height: 100%;
  overflow: auto;
}
.record-first-review.queue-collapsed {
  grid-template-columns: minmax(560px, 1.8fr) minmax(360px, 1fr);
}
.record-first-review.queue-collapsed .records-pane {
  display: none;
}
.queue-toggle {
  font-size: 0.8125rem;
}
.records-pane {
  background: var(--soft);
  border-inline-end: 1px solid var(--line);
}
.records-pane .pane-head {
  position: sticky;
  top: 0;
  z-index: 4;
  background: var(--soft);
  min-height: 46px;
  padding: 12px;
  font-size: 0.8125rem;
}
.record-row {
  min-height: 76px;
  padding: 10px 11px;
  gap: 9px;
}
.record-row span > b {
  font-size: 0.8125rem;
}
.record-row small {
  font-size: 0.8125rem;
  line-height: 1.35;
}
.record-row-status {
  display: inline-flex;
  width: max-content;
  margin-top: 5px;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--soft);
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: 800;
}
.record-row-status[data-state="metadata"],
.record-row-status[data-state="topology"],
.record-row-status[data-state="source"] {
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.record-row-status[data-state="rejected"] {
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.record-row-status[data-state="accepted"] {
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
}
.record-issue-summary {
  margin-top: 3px;
  color: var(--muted);
}
.record-review-pane {
  display: flex;
  flex-direction: column;
  background: var(--card);
}
.record-review-head {
  padding: 14px 20px;
}
.record-review-head h3 {
  font-size: 1.0625rem;
}
.record-review-head p {
  font-size: 0.8125rem;
}
.record-primary-text {
  flex: 1;
  max-width: 76ch;
  width: 100%;
  padding: 30px 38px;
  font:
    17px/1.72 Georgia,
    serif;
}
.review-reason {
  margin: 14px 20px 0;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.metadata-accept-blocker {
  margin: 0 20px 14px;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.decision-bar {
  min-height: 64px;
  padding: 11px 14px;
}
.decision-bar .btn {
  min-height: 40px;
  font-size: 0.8125rem;
}
.decision-actions .primary {
  min-width: 132px;
  font-weight: 800;
}
.review-inspector {
  background: var(--card);
  border-inline-start: 1px solid var(--line);
}
.review-inspector-tabs button {
  min-height: 48px;
  font-size: 0.8125rem;
}
.review-inspector-tabs button span {
  font-size: 0.8125rem;
}
.inspector-help {
  font-size: 0.8125rem;
}
.source-inspector-head {
  font-size: 0.8125rem;
}
.source-block p {
  font-size: 0.8125rem;
  line-height: 1.5;
}
.source-block header {
  font-size: 0.8125rem;
}
.build-summary:has(+ .review-session-bar) {
  padding-bottom: 4px;
}
@media (max-width: 1350px) {
  .record-first-review {
    grid-template-columns: minmax(210px, 240px) minmax(500px, 1.55fr) minmax(320px, 0.85fr);
  }
}
.source-tool-section {
  min-width: 0;
  border-top: 1px solid var(--line);
  background: var(--card);
}
.source-tool-section > summary {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 10px 12px;
  font-weight: 800;
  cursor: pointer;
}
.source-tool-section :deep(.boundary-adjudication) {
  border: 0;
  border-radius: 0;
}
.source-block,
.source-blocks,
.source-text-details {
  min-width: 0;
}
.source-block p,
.source-block header,
.original-extraction-snapshot {
  overflow-wrap: anywhere;
  max-width: 100%;
}
.review-inspector {
  overflow-x: hidden;
}
.builder-message {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.builder-message.warning {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.message-dismiss {
  flex: 0 0 auto;
  min-width: 36px;
  min-height: 36px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  font-size: 1.25rem;
  cursor: pointer;
}
.message-dismiss:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}

.record-row-wrap {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  align-items: stretch;
  border-bottom: 1px solid var(--line);
}
.record-row-wrap .record-row {
  border-bottom: 0;
}
.record-select {
  display: grid;
  place-items: center;
  min-width: 36px;
  cursor: pointer;
}
.record-select input,
.select-visible input {
  inline-size: 18px;
  block-size: 18px;
  accent-color: var(--accent);
}
.select-visible {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8125rem !important;
  font-weight: 650;
  color: var(--muted);
  cursor: pointer;
}
.review-session-title small {
  font-size: 0.8125rem !important;
  color: var(--muted);
  font-weight: 500;
  overflow-wrap: anywhere;
}

/* Accessible type floor for dense Corpus Builder controls. Keep status/meta text readable at zoom and in both locales. */
.corpus-builder small,
.corpus-builder label,
.corpus-builder summary,
.corpus-builder code {
  font-size: 0.8125rem !important;
  line-height: 1.4;
}
.corpus-builder
  :where(
    .eyebrow,
    .builder-setup label,
    .builder-setup small,
    .setup-card-heading small,
    .advanced-config summary,
    .escalation-field b,
    .escalation-field small,
    .launch-copy b,
    .launch-copy span,
    .context-blocker,
    .rail-title b,
    .rail-title span,
    .pane-head b,
    .pane-head span,
    .build-row b,
    .build-row small,
    .summary-top p,
    .build-status-line,
    .provenance-strip,
    .validation-strip,
    .provider-model-summary,
    .review-handoff b,
    .review-handoff span,
    .review-handoff > strong,
    .review-toolbar,
    .source-page-nav,
    .source-block header,
    .split-button,
    .evidence-toggle,
    .record-row b,
    .record-row small,
    .inspector-pane summary,
    .help,
    .active-build-settings > summary,
    .active-build-settings > div,
    .technical-details > summary,
    .record-review-head p,
    .review-stage-summary b,
    .review-stage-summary > span,
    .review-inspector-tabs button,
    .review-inspector-tabs button span,
    .inspector-help,
    .review-readonly-banner span,
    .pager,
    .record-row-status,
    .source-inspector-head
  ) {
  font-size: 0.8125rem !important;
  line-height: 1.4;
}
.source-head-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
.source-head-actions .btn {
  min-height: 36px;
  font-size: 0.8125rem;
}
@media (max-width: 760px) {
  .source-head-actions {
    justify-content: flex-start;
  }
  .source-inspector-head {
    align-items: flex-start;
    flex-direction: column;
  }
}

/* Feral Fox review and enrichment controls. */
.enrichment-strategy {
  display: grid;
  gap: 12px;
}
.mode-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.mode-options > label,
.semantic-index-toggle {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  cursor: pointer;
}
.mode-options input,
.semantic-index-toggle input,
.resolve-source-check input {
  inline-size: 18px;
  block-size: 18px;
  flex: 0 0 auto;
  margin-top: 2px;
  accent-color: var(--accent);
}
.mode-options span,
.semantic-index-toggle span {
  display: grid;
  gap: 4px;
}
.mode-options b,
.semantic-index-toggle b {
  font-size: 0.875rem;
}
.mode-options small,
.semantic-index-toggle small {
  font-size: 0.8125rem !important;
  color: var(--muted);
}
.mode-options > label:has(input:checked) {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 18%, transparent);
}
.mode-options > label:focus-within,
.semantic-index-toggle:focus-within {
  outline: 3px solid color-mix(in srgb, var(--accent) 35%, transparent);
  outline-offset: 2px;
}
.semantic-index-toggle:has(input:disabled) {
  opacity: 0.7;
  cursor: not-allowed;
}
.capacity-note {
  display: block;
  margin-top: 4px;
  font-size: 0.8125rem !important;
  color: var(--muted);
}
.record-text-review {
  display: grid;
  gap: 10px;
  margin: 14px 20px 0;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
  background: var(--card);
}
.record-text-review > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--soft);
}
.record-text-review > header > div {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.record-text-review > header b {
  font-size: 0.875rem;
}
.human-corrected {
  display: inline-flex;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
  font-size: 0.8125rem;
  font-weight: 800;
}
.record-text-review .record-primary-text {
  padding: 20px 24px;
  min-height: 220px;
  max-height: 62vh;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.record-text-editor {
  width: calc(100% - 24px);
  min-height: 330px;
  height: min(62vh, 720px);
  max-height: 72vh;
  overflow-y: auto;
  overscroll-behavior: contain;
  margin: 0 12px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  color: var(--text);
  font:
    16px/1.65 Georgia,
    serif;
  resize: vertical;
}
.record-text-editor:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.text-review-actions {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: grid;
  gap: 10px;
  padding: 10px 12px 12px;
  border-top: 1px solid var(--line);
  background: var(--card);
  box-shadow: 0 -8px 18px rgb(15 23 42 / 0.06);
}
.text-review-actions > div {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.record-text-head-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.text-save-hint {
  margin-inline-end: auto;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.4;
}
.resolve-source-check {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 8px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.original-extraction-snapshot {
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  padding: 12px;
  margin: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
  font:
    12px/1.5 ui-monospace,
    SFMono-Regular,
    Consolas,
    monospace;
}
.rerun-family {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.8125rem;
}
.rerun-family .control {
  min-width: 190px;
  min-height: 36px;
  font-size: 0.8125rem;
}
.data-actions {
  flex-wrap: wrap;
  align-items: center;
}
.corpus-builder
  :where(
    .build-guidance p,
    .build-guidance small,
    .manifest-gate p,
    .segmentation-blocked p,
    .segmentation-blocked details,
    .build-warning,
    .warnings,
    .metadata-json,
    .evidence-list b,
    .evidence-list span,
    .evidence-list small,
    .rail-empty,
    .inspector-empty,
    .builder-empty
  ) {
  font-size: 0.8125rem !important;
  line-height: 1.45;
}
/* 0.48.1 Gifted Grungus — visible review feedback and dedicated metadata workspaces. */
.review-action-feedback {
  grid-column: 1/-1;
  margin: 0;
  padding: 9px 11px;
  border: 1px solid var(--tone-ok-edge);
  border-radius: 9px;
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
  font-size: 0.8125rem;
  line-height: 1.5;
  font-weight: 650;
}
.document-metadata-launch {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin: 12px 14px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.document-metadata-launch > div {
  display: grid;
  gap: 3px;
}
.document-metadata-launch b {
  font-size: 0.875rem;
}
.document-metadata-launch span {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--muted);
}
@media (max-width: 760px) {
  .document-metadata-launch {
    align-items: stretch;
    flex-direction: column;
  }
  .document-metadata-launch .btn {
    width: 100%;
  }
}

/* 0.59.0 Serious Sandpipers — Corpus Builder workflow composition. */
.builder-setup {
  container-type: inline-size;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  border: 0;
  background: transparent;
  border-radius: 0;
  padding: 0;
  max-width: 1440px;
  width: 100%;
  margin-inline: auto;
}
.setup-section,
.setup-phase {
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
  box-shadow: 0 1px 2px rgb(15 23 42 / 0.035);
}
.setup-source-section {
  display: grid;
  gap: 13px;
  padding: 16px 18px;
}
.setup-section-head > div,
.phase-label {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.setup-section-head h3,
.phase-label h3 {
  margin: 0;
  font-size: 1rem;
}
.setup-section-head p,
.phase-label p {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.45;
  max-width: 86ch;
}
.setup-step {
  display: grid;
  place-items: center;
  flex: 0 0 30px;
  inline-size: 30px;
  block-size: 30px;
  border-radius: 50%;
  background: var(--soft);
  border: 1px solid var(--line);
  font-size: 0.8125rem;
  font-weight: 850;
}
.source-setup-grid {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) auto;
  gap: 12px;
  align-items: end;
}
.source-setup-grid label {
  display: grid;
  gap: 5px;
}
.source-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.source-facts {
  display: flex;
  gap: 8px 14px;
  flex-wrap: wrap;
  color: var(--muted);
  font-size: 0.8125rem;
}
.source-facts span {
  overflow-wrap: anywhere;
}
.setup-phase {
  display: grid;
  gap: 12px;
  padding: 16px;
}
.phase-label {
  padding: 0 2px;
}
.document-structure-config {
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
}
.setup-disclosure {
  overflow: hidden;
}
.setup-disclosure > summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 66px;
  padding: 12px 16px;
}
.setup-disclosure > summary::-webkit-details-marker {
  display: none;
}
.setup-disclosure > summary > span:last-child {
  display: grid;
  gap: 2px;
}
.setup-disclosure > summary b {
  font-size: 0.9375rem;
}
.setup-disclosure > summary small {
  color: var(--muted);
  font-size: 0.8125rem !important;
  font-weight: 500;
}
.setup-disclosure[open] > summary {
  border-bottom: 1px solid var(--line);
  background: var(--soft);
}
.setup-disclosure-body {
  display: grid;
  gap: 16px;
  padding: 16px;
}
.provider-area {
  padding: 0;
  border: 0;
}
.enrichment-strategy {
  padding-top: 2px;
}
.included-feature {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.included-feature b {
  font-size: 0.875rem;
}
.included-feature span {
  color: var(--muted);
  font-size: 0.8125rem;
}
.execution-wrapper {
  padding: 14px 16px;
}
.setup-section-inline-head {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;
}
.setup-section-inline-head > span:last-child {
  display: grid;
  gap: 2px;
}
.setup-section-inline-head b {
  font-size: 0.9375rem;
}
.setup-section-inline-head small {
  font-size: 0.8125rem !important;
  color: var(--muted);
}
.execution-wrapper > .execution-config {
  border: 0;
}
.execution-wrapper :deep(.execution-settings-shell) {
  border: 0;
}
.build-launch-row {
  display: none;
}
.workspace-switcher {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}
.workspace-switcher .btn[aria-pressed="true"] {
  border-color: var(--accent);
  background: var(--soft);
  box-shadow: inset 0 -2px 0 var(--accent);
}
.record-first-review.detail-mode {
  grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
}
.record-first-review.detail-mode.queue-collapsed {
  grid-template-columns: minmax(0, 1fr);
}
.record-first-review.detail-mode .record-review-pane {
  display: none;
}
.record-first-review.detail-mode .review-inspector {
  grid-column: auto;
  border-inline-start: 1px solid var(--line);
  background: var(--card);
}
.detail-workspace-head {
  position: sticky;
  top: 0;
  z-index: 7;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--line);
  background: var(--card);
}
.detail-workspace-head h3 {
  margin: 2px 0 4px;
  font-size: 1.05rem;
}
.detail-workspace-head p {
  margin: 0;
  max-width: 78ch;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.5;
}
.detail-mode .review-inspector-tabs {
  top: 94px;
}
.detail-mode .metadata-review {
  padding: 16px 18px;
}
.detail-mode .source-review-panel {
  padding-bottom: 18px;
}
.detail-mode .source-review-panel > .source-summary {
  max-width: 1100px;
  margin-inline: auto;
}
.detail-mode .source-tool-section {
  max-width: 1100px;
  margin-inline: auto;
}
.detail-mode .review-inspector {
  overflow-x: hidden;
}
@container (max-width:760px) {
  .source-setup-grid {
    grid-template-columns: 1fr;
  }
  .source-actions {
    display: grid;
  }
  .source-actions .btn {
    width: 100%;
  }
  .mode-options {
    grid-template-columns: 1fr;
  }
  .setup-section-head > div,
  .phase-label {
    align-items: flex-start;
  }
}
@media (max-width: 900px) {
  .source-setup-grid {
    grid-template-columns: 1fr;
  }
  .source-actions .btn {
    flex: 1 1 200px;
  }
  .setup-section-head > div,
  .phase-label {
    align-items: flex-start;
  }
}
@media (max-width: 620px) {
  .setup-source-section,
  .setup-phase,
  .setup-disclosure-body,
  .execution-wrapper {
    padding: 13px;
  }
  .source-actions {
    display: grid;
  }
  .source-actions .btn {
    width: 100%;
  }
  .setup-disclosure > summary {
    padding: 11px 13px;
  }
}
@media (max-width: 1050px) {
  .workspace-switcher {
    grid-column: 1/-1;
  }
  .record-first-review.detail-mode {
    grid-template-columns: 1fr;
  }
  .record-first-review.detail-mode .records-pane {
    max-height: 260px;
  }
  .detail-mode .review-inspector-tabs {
    top: 0;
  }
  .detail-workspace-head {
    position: static;
  }
}
/* Review workspace: one frame that fills the screen under the top bar, one scroll per pane. */
.builder-workspace.review-mode {
  overflow: clip;
}
.review-frame {
  display: flex;
  flex-direction: column;
  min-width: 0;
  scroll-margin-top: var(--ref-topbar, 60px);
}
.review-frame .review-toolbar {
  position: static;
  flex: 0 0 auto;
  border-radius: 12px 12px 0 0;
  border-bottom: 0;
}
.review-frame .review-grid.record-first-review {
  position: relative;
  overflow: hidden;
  flex: 1 1 auto;
  min-height: 0;
  grid-template-rows: minmax(0, 1fr);
  grid-template-columns: var(--rw-queue, 18rem) 0.5rem minmax(0, 1fr) 0.5rem var(
      --rw-inspector,
      25rem
    );
  border: 1px solid var(--line);
  border-radius: 0 0 12px 12px;
}
.review-frame .review-grid.queue-collapsed {
  grid-template-columns: minmax(0, 1fr) 0.5rem var(--rw-inspector, 25rem);
}
.review-frame .review-grid.detail-mode {
  grid-template-columns: var(--rw-queue, 18rem) 0.5rem minmax(0, 1fr);
}
.review-frame .review-grid.detail-mode.queue-collapsed {
  grid-template-columns: minmax(0, 1fr);
}
/* Each pane is its own positioned scroll box. An unpositioned pane let the queue's visually-hidden
   labels escape its clipping and stretch the whole page by several thousand pixels. */
/* Scrolling passes to the page at the edge of a pane. The frame fills the window, so a pane that swallowed
   the wheel would leave everything above the workspace unreachable. */
.review-frame .records-pane,
.review-frame .record-review-pane,
.review-frame .review-inspector {
  position: relative;
  height: 100%;
  min-height: 0;
  max-height: none;
  overflow: auto;
  overscroll-behavior: auto;
}
/* The text card is a flex item with overflow:hidden, which lets it shrink below its content and clip the end of a long record. It keeps its full height and the pane scrolls instead. */
.review-frame .record-text-review {
  flex: none;
  margin-block-end: 14px;
}
.review-frame .record-text-review .record-primary-text {
  max-height: none;
  overflow: visible;
}
.review-splitter {
  position: relative;
  cursor: col-resize;
  touch-action: none;
  background: var(--card);
  border-inline: 1px solid var(--line);
}
.review-splitter::before {
  content: "";
  position: absolute;
  inset-block: 0;
  inset-inline: -0.5rem;
}
.review-splitter::after {
  content: "";
  position: absolute;
  inset-block: calc(50% - 1.5rem);
  inset-inline: 0.1875rem;
  border-radius: 2px;
  background: var(--line-strong);
}
.review-splitter:hover::after,
.review-splitter:focus-visible::after {
  background: var(--accent-fg);
}
.review-splitter:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: -2px;
}
:global(body.splitter-dragging) {
  cursor: col-resize;
  user-select: none;
}
/* Wide and medium screens: the frame fills the screen under the top bar. */
@media (min-width: 800px) and (min-height: 34rem) {
  .review-frame {
    position: sticky;
    top: var(--ref-topbar, 60px);
    height: calc(100dvh - var(--ref-topbar, 60px) - 0.75rem);
    min-height: 30rem;
  }
}
/* Medium (a laptop): the queue and the record side by side, the inspector as a full-width pane below. */
@media (min-width: 800px) and (max-width: 1279.98px) and (min-height: 34rem) {
  .review-frame .review-grid.record-first-review {
    grid-template-columns: var(--rw-queue, 16rem) 0.5rem minmax(0, 1fr);
    grid-template-rows: minmax(0, 1.9fr) minmax(0, 1fr);
  }
  .review-frame .review-grid.queue-collapsed {
    grid-template-columns: minmax(0, 1fr);
  }
  .review-frame .review-grid .review-splitter[data-splitter="inspector"] {
    display: none;
  }
  .review-frame .review-inspector {
    grid-column: 1/-1;
    border-inline-start: 0;
    border-top: 1px solid var(--line);
  }
  .review-frame .review-grid.detail-mode {
    grid-template-columns: var(--rw-queue, 16rem) 0.5rem minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
  }
  .review-frame .review-grid.detail-mode .records-pane {
    grid-row: 1;
  }
  .review-frame .review-grid.detail-mode .review-inspector {
    grid-column: 3;
    grid-row: 1;
    border-top: 0;
  }
  .review-frame .review-grid.detail-mode.queue-collapsed {
    grid-template-columns: minmax(0, 1fr);
  }
  .review-frame .review-grid.detail-mode.queue-collapsed .review-inspector {
    grid-column: 1;
  }
}
/* Phones and very short windows: an ordinary page, panes at their natural height. */
@media (max-width: 799.98px), (max-height: 33.99rem) {
  .review-splitter {
    display: none;
  }
  .review-frame .review-grid.record-first-review,
  .review-frame .review-grid.queue-collapsed,
  .review-frame .review-grid.detail-mode,
  .review-frame .review-grid.detail-mode.queue-collapsed {
    overflow: visible;
    grid-template-rows: auto;
    grid-template-columns: minmax(0, 1fr);
  }
  .review-frame .records-pane {
    max-height: 18rem;
    height: auto;
  }
  .review-frame .record-review-pane,
  .review-frame .review-inspector {
    height: auto;
    overflow: visible;
  }
}
/* Below the wide layout the toolbar wraps instead of overflowing. */
@media (max-width: 1279.98px) {
  .review-frame .review-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
  }
  .review-frame .review-toolbar > :first-child {
    flex: 1 1 100%;
  }
  .review-frame .review-toolbar .pager {
    order: 9;
    margin-inline-start: auto;
  }
  .review-frame .review-toolbar #pdf-corpus-record-search {
    flex: 1 1 12rem;
  }
  .review-frame .review-toolbar .review-bulk {
    flex-wrap: wrap;
  }
  .review-frame .review-toolbar .review-action-feedback,
  .review-frame .review-toolbar > :is(section, form, aside) {
    flex: 1 1 100%;
  }
}

/* The decision dock: one row, always in reach, primary action last. */
.review-frame .record-review-pane {
  display: flex;
  flex-direction: column;
  container: record/inline-size;
}
.record-decision-dock {
  position: sticky;
  bottom: 0;
  z-index: 5;
  margin-block-start: auto;
  border-top: 1px solid var(--line);
  background: var(--card);
}
.record-decision-dock .metadata-accept-blocker {
  margin: 0;
  padding: 0.5rem 0.875rem;
  border-bottom: 1px solid var(--line);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.record-decision-dock .text-edit-bar .text-save-hint {
  flex: 1 1 14rem;
  font-size: 0.8125rem;
  color: var(--muted);
}
.record-decision-dock .decision-bar {
  position: static;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem 0.75rem;
  min-height: 0;
  padding: 0.625rem 0.875rem;
  border-top: 0;
  background: transparent;
  backdrop-filter: none;
}
.decision-history,
.decision-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.decision-actions {
  margin-inline-start: auto;
}
.decision-history .btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}
.decision-history .btn svg {
  inline-size: 1rem;
  block-size: 1rem;
}
.flip-inline {
  transform: scaleX(-1);
}
/* A narrow record pane keeps Undo and Redo to their icons (the words stay for assistive technology). */
@container record (max-width:30rem) {
  .decision-history .btn-text {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
  }
  .decision-history .btn {
    padding-inline: 0.625rem;
  }
}
/* When the pane is tight, More actions shrinks to its dots so the dock stays on one row. */
@container record (max-width:33rem) {
  .record-decision-dock :deep(.action-menu-label),
  .record-decision-dock :deep(.action-menu-caret) {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
  }
  .record-decision-dock :deep(.action-menu-dots) {
    display: inline-block;
  }
  .record-decision-dock :deep(.action-menu-trigger) {
    min-inline-size: 2.5rem;
    justify-content: center;
  }
  .record-head-actions {
    flex-wrap: nowrap;
  }
}
@container record (max-width:24rem) {
  .record-decision-dock .decision-bar {
    flex-direction: column-reverse;
    align-items: stretch;
  }
  .decision-actions {
    margin-inline-start: 0;
  }
  .decision-actions .btn {
    flex: 1 1 0;
  }
  .record-decision-dock .action-menu,
  .record-decision-dock :deep(.action-menu-trigger) {
    inline-size: 100%;
  }
}

/* Queue rows: a state icon (a shape, not only a colour), the id, where it is, and the state once. */
.review-frame .record-row {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr);
  gap: 0.625rem;
  align-items: start;
  min-height: 0;
  padding: 0.625rem 0.75rem;
}
.record-state-icon {
  display: grid;
  place-items: center;
  inline-size: 1.25rem;
  block-size: 1.25rem;
  margin-block-start: 0.0625rem;
  box-sizing: border-box;
  border: 2px solid var(--muted);
  border-radius: 50%;
  color: var(--muted);
}
.record-state-icon svg {
  inline-size: 0.75rem;
  block-size: 0.75rem;
}
.record-state-icon[data-state="accepted"] {
  border-color: var(--tone-ok-border);
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
}
.record-state-icon[data-state="rejected"] {
  border-color: var(--tone-danger-border);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.record-state-icon[data-state="metadata"],
.record-state-icon[data-state="topology"],
.record-state-icon[data-state="source"] {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.record-state-icon[data-state="ready"] {
  border-color: var(--tone-ok-border);
  color: var(--tone-ok-fg);
}
.record-row-main {
  display: grid;
  gap: 0.125rem;
  min-width: 0;
}
.record-row-main b {
  overflow-wrap: anywhere;
}
.record-head-actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
}
.review-frame .record-review-head > div:first-child {
  min-width: 0;
  flex: 1 1 8rem;
}
.review-frame .record-review-head h3 {
  overflow-wrap: anywhere;
}
/* The toolbar is two rows on a wide screen: the queues, then search, workspace and bulk actions. */
.review-frame .review-toolbar {
  gap: 0.5rem 0.75rem;
  align-items: center;
  padding: 0.5rem 0.75rem;
}
@media (min-width: 1280px) {
  .review-frame .review-toolbar {
    display: grid;
    grid-template-columns: minmax(10rem, 1fr) auto auto;
  }
  .review-frame .review-toolbar > :first-child {
    grid-column: 1/3;
  }
  .review-frame .review-toolbar .pager {
    grid-column: 3;
    grid-row: 1;
    justify-self: end;
  }
  .review-frame .review-toolbar #pdf-corpus-record-search {
    grid-column: 1;
  }
  .review-frame .review-toolbar .workspace-switcher {
    grid-column: 2;
  }
  .review-frame .review-toolbar .review-bulk {
    grid-column: 3;
    flex-wrap: nowrap;
    justify-content: flex-end;
  }
  .review-frame .review-toolbar .review-action-feedback {
    grid-column: 1/-1;
    margin: 0;
  }
  .review-frame .review-toolbar > :is(section, form, aside) {
    grid-column: 1/-1;
  }
}
/* The queue header: the title and count, then the select-all control and the hide control. */
.review-frame .records-pane .pane-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas: "title count" "select hide";
  align-items: center;
  gap: 0.25rem 0.5rem;
  min-height: 0;
  padding: 0.5rem 0.75rem;
}
.review-frame .records-pane .pane-head > b {
  grid-area: title;
}
.review-frame .records-pane .pane-head > span {
  grid-area: count;
}
.review-frame .records-pane .pane-head > .select-visible {
  grid-area: select;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 1.5rem;
}
.review-frame .records-pane .pane-head > .queue-toggle {
  grid-area: hide;
  justify-self: end;
}
@media (max-width: 650px) {
  .record-decision-dock {
    bottom: 52px;
  }
}
/* Compact review. A 768-pixel laptop should show a record, its controls and its decisions without scrolling the page: the
   headings that repeat what the queue row already says give way to the text, and the actions stay on one line. */
.review-frame .record-review-head {
  padding: 10px 16px;
}
.review-frame .record-review-head .eyebrow {
  display: none;
}
.review-frame .record-review-head h3 {
  margin: 0;
  font-size: 1rem;
}
.review-frame .record-review-head p {
  margin: 2px 0 0;
}
.review-frame .record-text-review > header {
  flex-wrap: nowrap;
  padding: 6px 10px;
}
.review-frame .record-text-review > header b {
  white-space: nowrap;
}
.review-frame .record-text-head-actions {
  display: flex;
  flex-wrap: nowrap;
  gap: 6px;
  flex: none;
}
.review-frame .record-text-head-actions .btn {
  white-space: nowrap;
}
.review-frame .record-decision-dock .metadata-accept-blocker {
  padding: 0.375rem 0.875rem;
}
@media (max-height: 860px) {
  .review-frame .record-decision-dock .metadata-accept-blocker b {
    display: none;
  }
  .review-frame .record-review-head p {
    font-size: 0.75rem;
  }
}
.schema-choice {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
}
.schema-choice-field {
  display: grid;
  gap: 4px;
  flex: 1 1 16rem;
  font-size: 0.8125rem;
  font-weight: 700;
}
.schema-choice-field small {
  color: var(--muted);
  font-weight: 500;
}
</style>
