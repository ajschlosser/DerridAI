Warning: truncated output (original token count: 69016)
Total output lines: 8289

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
  const viewport = captureReviewViewport(…39016 tokens truncated…dReviewIds]"
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
