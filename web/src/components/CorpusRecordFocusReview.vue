<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusRecord, SourceBlock } from "../api/pdfCorpus";
import type { MetadataSchema } from "../api/metadataSchemas";
import type { ProviderProfile } from "../api/system";
import AppIcon from "./AppIcon.vue";
import type { CorpusActionMenuItem } from "./CorpusActionMenu.vue";
import CorpusMetadataResolutionPanel from "./CorpusMetadataResolutionPanel.vue";
import CorpusReviewQueueContext from "./CorpusReviewQueueContext.vue";
import CorpusFocusHeader from "./corpus-builder/CorpusFocusHeader.vue";
import CorpusSourceIssuePanel from "./CorpusSourceIssuePanel.vue";
import CorpusRecordDecisionDock from "./corpus-builder/CorpusRecordDecisionDock.vue";
import CorpusReviewEvidencePanel from "./corpus-builder/CorpusReviewEvidencePanel.vue";
import CorpusReviewSourcePanel from "./corpus-builder/CorpusReviewSourcePanel.vue";
import RecordContextReader from "./corpus-builder/RecordContextReader.vue";

/**
 * Focus View: the review workspace without the queue and chrome. It is a layout, not a second implementation: the
 * reader, metadata, evidence, source and decision dock are the same components the workspace uses.
 */
type InspectorTab = "metadata" | "evidence" | "source";
const props = withDefaults(
  defineProps<{
    record: CorpusRecord;
    buildId?: string;
    schema?: MetadataSchema | null;
    busy?: boolean;
    /** The review is still being prepared; deciding waits. */
    locked?: boolean;
    regionTypes?: string[];
    discourseRoles?: string[];
    confidenceCalibration?: Record<string, Record<string, Record<string, number>>>;
    knownValues?: Record<string, string[]>;
    blockingFields?: string[];
    savingField?: string;
    savedField?: string;
    batchSaving?: boolean;
    actionItems?: CorpusActionMenuItem[];
    // Queue and history position.
    canHistoryBack?: boolean;
    canHistoryForward?: boolean;
    canPreviousRecord?: boolean;
    canNextRecord?: boolean;
    justProcessedRecordId?: string;
    nextRecordId?: string;
    /** Build-wide progress, shown as a slim strip so the session never loses its bearings. */
    accepted?: number;
    remaining?: number;
    total?: number;
    // Text editing (owned by the parent).
    editingText?: boolean;
    textDraft?: string;
    resolveSourceIssues?: boolean;
    showContext?: boolean;
    inspectorTab?: InspectorTab;
    // Evidence.
    evidenceFields?: string[];
    selectedEvidenceField?: string;
    evidenceBlockIds?: string[];
    paginatedSource?: boolean;
    // Source.
    sourceBlocks?: SourceBlock[];
    sourcePageBlocks?: SourceBlock[];
    mediaKind?: string;
    audioUrl?: string;
    imageUrl?: string;
    showPdfExplorer?: boolean;
    sourcePdfUrl?: string;
    sourcePdfPage?: number;
    sourcePdfPageCount?: number;
    sourcePageWidth?: number;
    sourcePageHeight?: number;
    canPreviousSourcePage?: boolean;
    canNextSourcePage?: boolean;
    canMergePrevious?: boolean;
    canMergeNext?: boolean;
    providerProfiles?: ProviderProfile[];
    llmProviderProfileId?: string;
    llmModelOverride?: string;
    activeRequests?: number;
  }>(),
  {
    buildId: "",
    schema: null,
    regionTypes: () => [],
    discourseRoles: () => [],
    confidenceCalibration: () => ({}),
    knownValues: () => ({}),
    blockingFields: () => [],
    savingField: "",
    savedField: "",
    actionItems: () => [],
    accepted: 0,
    remaining: 0,
    total: 0,
    showContext: true,
    inspectorTab: "metadata",
    evidenceFields: () => [],
    selectedEvidenceField: "",
    evidenceBlockIds: () => [],
    paginatedSource: true,
    sourceBlocks: () => [],
    sourcePageBlocks: () => [],
    showPdfExplorer: true,
    sourcePdfUrl: "",
    sourcePdfPage: 1,
    sourcePdfPageCount: 0,
    sourcePageWidth: 0,
    sourcePageHeight: 0,
    providerProfiles: () => [],
    llmProviderProfileId: "",
    llmModelOverride: "",
    activeRequests: 0,
  },
);
const emit = defineEmits<{
  close: [];
  accept: [];
  reject: [];
  skip: [];
  undo: [];
  redo: [];
  historyBack: [];
  historyForward: [];
  previousRecord: [];
  nextRecord: [];
  recordAction: [id: string];
  focusBlocker: [];
  openSourceIssue: [];
  adjudicateBoundary: [direction: "previous" | "next", providerProfileId: string, model: string];
  openSourceViewer: [];
  openPdfExplorer: [];
  previousSourcePage: [];
  nextSourcePage: [];
  splitAfter: [blockId: string];
  updateLlmProviderProfile: [value: string];
  updateLlmModel: [value: string];
  beginTextEdit: [proposal?: boolean];
  cancelTextEdit: [];
  saveText: [];
  markTextReviewed: [];
  textDraftChange: [value: string];
  resolveSourceIssuesChange: [value: boolean];
  "update:showContext": [value: boolean];
  "update:inspectorTab": [value: InspectorTab];
  openTextCleanup: [];
  resolveMetadata: [field: string, value: unknown];
  resolveMetadataMany: [changes: Record<string, unknown>];
  confirmNoMetadataValue: [field: string];
  metadataDirty: [dirty: boolean];
  llmTouchup: [text: string];
  navigateRecord: [recordId: string];
  selectEvidence: [field: string];
  toggleEvidence: [blockId: string];
  resolveMetadataWithEvidence: [field: string, value: unknown, text: string];
}>();
const i18n = useI18nStore();
const dialog = ref<HTMLElement | null>(null);
const head = ref<InstanceType<typeof CorpusFocusHeader> | null>(null);
const dock = ref<InstanceType<typeof CorpusRecordDecisionDock> | null>(null);
const priorActive = ref<HTMLElement | null>(null);
const tabOrder: InspectorTab[] = ["metadata", "evidence", "source"];
const tab = computed(() => props.inspectorTab);

const blockingLabel = computed(() =>
  props.blockingFields
    .map((field) => i18n.t(`record.${field}`, field.replace(/_/g, " ")))
    .join(", "),
);
const evidenceIds = computed(() => new Set(props.evidenceBlockIds));
const reasonKinds = computed(() => {
  const reason = String(props.record.review_reason || "");
  return reason && reason.toLowerCase() !== "pending human review." ? reason : "";
});
const guidanceMatches = computed(() =>
  Object.entries(props.record.metadata_guidance_matches || {}),
);
const textReviewLabel = computed(() =>
  props.record.text_review_status === "human_corrected"
    ? i18n.t("pdf_corpus.human_corrected")
    : props.record.text_review_status === "human_reviewed"
      ? i18n.t("pdf_corpus.human_reviewed")
      : "",
);
const canMarkReviewed = computed(
  () =>
    !props.editingText &&
    props.record.text_review_status !== "human_corrected" &&
    props.record.text_review_status !== "human_reviewed",
);

function setTab(next: InspectorTab) {
  emit("update:inspectorTab", next);
}
function focusables() {
  if (!dialog.value) return [] as HTMLElement[];
  return Array.from(
    dialog.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])',
    ),
  ).filter((node) => node.offsetParent !== null);
}
function handleKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && props.editingText) {
    event.preventDefault();
    requestSaveText();
    return;
  }
  if (event.altKey && event.key === "ArrowLeft" && props.canPreviousRecord) {
    event.preventDefault();
    emit("previousRecord");
    return;
  }
  if (event.altKey && event.key === "ArrowRight" && props.canNextRecord) {
    event.preventDefault();
    emit("nextRecord");
    return;
  }
  if (event.key === "Escape") {
    // An open menu or popover owns its own Escape (it closes itself and returns focus); only a bare Escape
    // leaves Focus View, so dismissing a menu never throws the reviewer out of the record.
    if ((event.target as HTMLElement | null)?.closest?.("[aria-expanded='true'], details[open]"))
      return;
    event.preventDefault();
    emit("close");
    return;
  }
  if (event.key !== "Tab") return;
  const nodes = focusables();
  if (nodes.length < 2) return;
  const first = nodes[0],
    last = nodes[nodes.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
function handleTabKeydown(event: KeyboardEvent) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  const current = tabOrder.indexOf(tab.value);
  let next = current;
  if (event.key === "Home") next = 0;
  else if (event.key === "End") next = tabOrder.length - 1;
  else if (event.key === "ArrowRight") next = (current + 1) % tabOrder.length;
  else next = (current - 1 + tabOrder.length) % tabOrder.length;
  setTab(tabOrder[next]);
  void nextTick(() =>
    dialog.value?.querySelector<HTMLButtonElement>(`#focus-tab-${tabOrder[next]}`)?.focus(),
  );
}
function requestSaveText() {
  if (!String(props.textDraft || "").trim()) return;
  emit("saveText");
}
function openFieldEvidence(field: string) {
  emit("selectEvidence", field);
  setTab("evidence");
}
/** Every pending field is decided: hand the keyboard to the record decision, so Enter accepts. */
function handleMetadataComplete() {
  void nextTick(() => dock.value?.focusAccept());
}
onMounted(() => {
  priorActive.value = document.activeElement as HTMLElement | null;
  document.documentElement.dataset.focusReview = "true";
  document.body.style.overflow = "hidden";
  void nextTick(() => head.value?.focusClose());
});
onBeforeUnmount(() => {
  delete document.documentElement.dataset.focusReview;
  document.body.style.overflow = "";
  priorActive.value?.focus?.({ preventScroll: true });
});
watch(
  () => props.record.record_id,
  () => {
    void nextTick(() =>
      dialog.value
        ?.querySelector<HTMLElement>(".focus-record-text")
        ?.focus({ preventScroll: true }),
    );
  },
);
</script>

<template>
  <section
    ref="dialog"
    class="focus-review"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="`focus-title-${record.record_id}`"
    @keydown="handleKeydown"
  >
    <CorpusFocusHeader
      ref="head"
      :record="record"
      :accepted="accepted"
      :remaining="remaining"
      :total="total"
      :can-history-back="canHistoryBack"
      :can-history-forward="canHistoryForward"
      :can-previous-record="canPreviousRecord"
      :can-next-record="canNextRecord"
      @close="emit('close')"
      @history-back="emit('historyBack')"
      @history-forward="emit('historyForward')"
      @previous-record="emit('previousRecord')"
      @next-record="emit('nextRecord')"
    />

    <main class="focus-workspace">
      <article class="focus-record" aria-labelledby="focus-record-heading">
        <header class="focus-record-heading">
          <div>
            <span class="eyebrow">{{ i18n.t("pdf_corpus.reviewed_record_text") }}</span>
            <h3 id="focus-record-heading">
              {{ i18n.t("pdf_corpus.proposed_record") }}
              <span v-if="textReviewLabel" class="human-corrected">{{ textReviewLabel }}</span>
            </h3>
          </div>
          <div class="heading-actions">
            <button
              v-if="record.source_quality_issues?.length"
              class="source-warn-icon"
              type="button"
              :aria-label="i18n.t('pdf_corpus.source_warning_icon')"
              :title="i18n.t('pdf_corpus.source_warning_icon')"
              @click="emit('openSourceIssue')"
            >
              <AppIcon name="warning" />
            </button>
            <label v-if="!editingText" class="context-toggle">
              <input
                type="checkbox"
                :checked="showContext"
                @change="emit('update:showContext', ($event.target as HTMLInputElement).checked)"
              />
              {{ i18n.t("pdf_corpus.context_show") }}
            </label>
            <template v-if="editingText">
              <button
                class="btn small"
                type="button"
                :disabled="busy"
                @click="emit('openTextCleanup')"
              >
                {{ i18n.t("pdf_corpus.clean_text") }}
              </button>
              <button
                class="btn small"
                type="button"
                :disabled="busy"
                @click="emit('llmTouchup', textDraft || '')"
              >
                {{ i18n.t("pdf_corpus.llm_touchup") }}
              </button>
            </template>
            <button
              v-if="canMarkReviewed"
              class="btn small"
              type="button"
              :disabled="busy"
              @click="emit('markTextReviewed')"
            >
              {{ i18n.t("pdf_corpus.mark_text_reviewed") }}
            </button>
            <button
              class="btn small"
              type="button"
              :disabled="busy"
              @click="editingText ? emit('cancelTextEdit') : emit('beginTextEdit', false)"
            >
              {{ editingText ? i18n.t("ui.cancel") : i18n.t("pdf_corpus.edit_text") }}
            </button>
          </div>
        </header>

        <aside
          v-if="record.text_touchup_proposal?.status === 'pending_review'"
          class="focus-note"
          data-tone="info"
          role="status"
        >
          <b>{{ i18n.t("pdf_corpus.llm_touchup_proposal_available") }}</b>
          <span>{{ i18n.t("pdf_corpus.llm_touchup_proposal_help") }}</span>
          <button
            class="btn small"
            type="button"
            :disabled="busy"
            @click="emit('beginTextEdit', true)"
          >
            {{ i18n.t("pdf_corpus.review_touchup_proposal") }}
          </button>
        </aside>
        <aside v-else-if="reasonKinds" class="focus-note" data-tone="warn" role="note">
          <b>{{ i18n.t("pdf_corpus.why_review") }}</b>
          <span>{{ reasonKinds }}</span>
        </aside>
        <p v-if="record.text_noise?.unusable" class="focus-note" data-tone="danger" role="status">
          {{ i18n.t("pdf_corpus.text_noise.unusable") }}
        </p>
        <CorpusReviewQueueContext
          :current-record-id="record.record_id"
          :just-processed-record-id="justProcessedRecordId"
          :next-record-id="nextRecordId"
          @navigate-record="emit('navigateRecord', $event)"
        />

        <div v-if="editingText" class="focus-text-edit">
          <textarea
            :value="textDraft || ''"
            class="focus-text-editor"
            :aria-label="i18n.t('pdf_corpus.reviewed_record_text')"
            @input="emit('textDraftChange', ($event.target as HTMLTextAreaElement).value)"
          ></textarea>
          <label v-if="record.source_quality_issues?.length" class="resolve-check">
            <input
              type="checkbox"
              :checked="resolveSourceIssues"
              @change="
                emit('resolveSourceIssuesChange', ($event.target as HTMLInputElement).checked)
              "
            />
            <span>{{ i18n.t("pdf_corpus.resolve_source_with_correction") }}</span>
          </label>
        </div>
        <div v-else class="focus-record-text" tabindex="-1">
          <RecordContextReader
            :build-id="buildId"
            :record-id="record.record_id"
            :text="record.text"
            :show-context="showContext"
            @select="emit('navigateRecord', $event)"
          />
        </div>
      </article>

      <aside class="focus-inspector" :aria-label="i18n.t('pdf_corpus.record_data')">
        <div
          class="focus-tabs"
          role="tablist"
          :aria-label="i18n.t('pdf_corpus.focus_detail_tabs')"
          @keydown="handleTabKeydown"
        >
          <button
            v-for="name in tabOrder"
            :id="`focus-tab-${name}`"
            :key="name"
            type="button"
            role="tab"
            :tabindex="tab === name ? 0 : -1"
            :aria-selected="tab === name"
            :aria-controls="`focus-panel-${name}`"
            @click="setTab(name)"
          >
            {{ i18n.t(`pdf_corpus.${name}_tab`) }}
            <span v-if="name === 'metadata' && blockingFields.length" class="focus-tab-count">{{
              blockingFields.length
            }}</span>
          </button>
        </div>

        <div class="focus-inspector-body">
          <section
            v-if="tab === 'metadata'"
            id="focus-panel-metadata"
            class="focus-panel focus-metadata-panel"
            role="tabpanel"
            aria-labelledby="focus-tab-metadata"
          >
            <CorpusMetadataResolutionPanel
              :schema="schema"
              :record="record"
              :region-types="regionTypes"
              :discourse-roles="discourseRoles"
              :busy="busy"
              :batch-saving="batchSaving"
              :saving-field="savingField"
              :saved-field="savedField"
              :confidence-calibration="confidenceCalibration"
              :known-values="knownValues"
              :blocking-fields="blockingFields"
              @complete="handleMetadataComplete"
              @resolve="(field, value) => emit('resolveMetadata', field, value)"
              @resolve-many="(changes) => emit('resolveMetadataMany', changes)"
              @no-value="(field) => emit('confirmNoMetadataValue', field)"
              @dirty="(value) => emit('metadataDirty', value)"
              @source="openFieldEvidence($event)"
              @resolve-with-evidence="
                (field, value, text) => emit('resolveMetadataWithEvidence', field, value, text)
              "
            />
          </section>

          <template v-else-if="tab === 'evidence'">
            <section
              v-if="guidanceMatches.length"
              class="focus-guidance"
              aria-labelledby="guidance-match-title"
            >
              <h3 id="guidance-match-title">{{ i18n.t("pdf_corpus.run_guidance_matches") }}</h3>
              <p>{{ i18n.t("pdf_corpus.run_guidance_matches_help") }}</p>
              <ul>
                <li v-for="[field, hits] in guidanceMatches" :key="field">
                  <b>{{ i18n.t(`record.${field}`, field.replace(/_/g, " ")) }}</b>
                  <span v-for="hit in hits" :key="`${hit.term}-${hit.occurrences}`"
                    >{{ hit.term }} ·
                    {{
                      i18n.tf("pdf_corpus.run_guidance_occurrences", { count: hit.occurrences })
                    }}</span
                  >
                </li>
              </ul>
            </section>
            <CorpusReviewEvidencePanel
              id-prefix="focus"
              :record="record"
              :fields="evidenceFields"
              :selected-field="selectedEvidenceField"
              :blocks="sourceBlocks"
              :evidence-block-ids="evidenceIds"
              :paginated-source="paginatedSource"
              :disabled="busy"
              @update:selected-field="emit('selectEvidence', $event)"
              @toggle-evidence="emit('toggleEvidence', $event)"
            />
          </template>

          <template v-else>
            <CorpusSourceIssuePanel
              v-if="record.source_quality_issues?.length"
              :issues="record.source_quality_issues"
            />
            <CorpusSourceIssuePanel
              v-else-if="record.resolved_source_quality_issues?.length"
              :issues="record.resolved_source_quality_issues"
              :resolved="true"
            />
            <CorpusReviewSourcePanel
              id-prefix="focus"
              :record="record"
              workspace-mode="record"
              :media-kind="mediaKind"
              :audio-url="audioUrl"
              :image-url="imageUrl"
              :show-pdf-explorer="showPdfExplorer"
              :pdf-url="sourcePdfUrl"
              :page="sourcePdfPage"
              :page-count="sourcePdfPageCount"
              :page-width="sourcePageWidth"
              :page-height="sourcePageHeight"
              :page-blocks="sourcePageBlocks"
              :visible-blocks="sourceBlocks"
              :evidence-ids="evidenceBlockIds"
              :evidence-block-ids="evidenceIds"
              :selected-evidence-field="selectedEvidenceField"
              :paginated-source="paginatedSource"
              :can-previous-source-page="Boolean(canPreviousSourcePage)"
              :can-next-source-page="Boolean(canNextSourcePage)"
              :can-merge-previous="Boolean(canMergePrevious)"
              :can-merge-next="Boolean(canMergeNext)"
              :profiles="providerProfiles"
              :provider-profile-id="llmProviderProfileId"
              :model-override="llmModelOverride"
              :active-requests="activeRequests"
              :disabled="busy"
              @previous-source-page="emit('previousSourcePage')"
              @next-source-page="emit('nextSourcePage')"
              @open-viewer="emit('openSourceViewer')"
              @open-pdf-explorer="emit('openPdfExplorer')"
              @update:provider-profile-id="emit('updateLlmProviderProfile', $event)"
              @update:model-override="emit('updateLlmModel', $event)"
              @adjudicate="
                (direction, profileId, model) =>
                  emit('adjudicateBoundary', direction, profileId, model)
              "
              @toggle-evidence="emit('toggleEvidence', $event)"
              @split="emit('splitAfter', $event)"
            />
          </template>
        </div>
      </aside>
    </main>

    <CorpusRecordDecisionDock
      ref="dock"
      blocker-id="focus-metadata-blocker"
      :accepted="Boolean(record.accepted)"
      :editing="editingText"
      :busy="busy"
      :locked="locked"
      :save-disabled="!String(textDraft || '').trim()"
      :blocking-count="blockingFields.length"
      :blocking-label="blockingLabel"
      :action-items="actionItems"
      @focus-blocker="emit('focusBlocker')"
      @undo="emit('undo')"
      @redo="emit('redo')"
      @action="emit('recordAction', $event)"
      @skip="emit('skip')"
      @reject="emit('reject')"
      @accept="emit('accept')"
      @cancel-edit="emit('cancelTextEdit')"
      @save-text="requestSaveText"
    />
  </section>
</template>

<style scoped src="../features/corpus-builder/CorpusRecordFocusReview.css"></style>
