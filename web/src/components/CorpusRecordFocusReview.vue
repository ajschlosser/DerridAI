<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusRecord, SourceBlock } from "../api/pdfCorpus";
import { hideSourceWarnings } from "../domain/sourceQuality";
import type { ProviderProfile } from "../api/system";
import CorpusSourceIssuePanel from "./CorpusSourceIssuePanel.vue";
import CorpusSourceQualityDialog from "./CorpusSourceQualityDialog.vue";
import CorpusMetadataResolutionPanel from "./CorpusMetadataResolutionPanel.vue";
import CorpusTextCleanupDialog from "./CorpusTextCleanupDialog.vue";
import CorpusRevisionHistory from "./CorpusRevisionHistory.vue";
import CorpusBoundarySliceDialog from "./CorpusBoundarySliceDialog.vue";
import CorpusBoundaryAdjudication from "./CorpusBoundaryAdjudication.vue";
import CorpusSourceSummary from "./CorpusSourceSummary.vue";
import CorpusReviewQueueContext from "./CorpusReviewQueueContext.vue";
import AppIcon from "./AppIcon.vue";

const props = defineProps<{
  record: CorpusRecord;
  sourceBlocks?: SourceBlock[];
  sourcePdfUrl?: string;
  sourcePdfPage?: number;
  sourcePdfPageCount?: number;
  sourcePageWidth?: number;
  sourcePageHeight?: number;
  busy?: boolean;
  canMergePrevious?: boolean;
  canMergeNext?: boolean;
  canAccept?: boolean;
  regionTypes?: string[];
  discourseRoles?: string[];
  recurringLines?: string[];
  documentTerms?: string[];
  confidenceCalibration?: Record<string, Record<string, Record<string, number>>>;
  canHistoryBack?: boolean;
  canHistoryForward?: boolean;
  canPreviousRecord?: boolean;
  canNextRecord?: boolean;
  providerProfiles?: ProviderProfile[];
  llmProviderProfileId?: string;
  llmModelOverride?: string;
  justProcessedRecordId?: string;
  nextRecordId?: string;
}>();
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
  requeueMetadata: [];
  merge: [direction: "previous" | "next"];
  slice: [direction: "previous" | "next" | "keep" | "new", offset: number, keepEnd?: number];
  adjudicateBoundary: [direction: "previous" | "next", providerProfileId: string, model: string];
  openSourceViewer: [];
  updateLlmProviderProfile: [value: string];
  updateLlmModel: [value: string];
  saveText: [text: string, resolveSourceIssues: boolean];
  resolveMetadata: [field: string, value: unknown];
  confirmNoMetadataValue: [field: string];
  metadataDirty: [dirty: boolean];
  previewJsonl: [];
  llmTouchup: [text: string];
  navigateRecord: [recordId: string];
}>();
const i18n = useI18nStore();
const dialog = ref<HTMLElement | null>(null);
const closeButton = ref<HTMLButtonElement | null>(null);
const tab = ref<"metadata" | "evidence" | "source">("metadata");
const priorActive = ref<HTMLElement | null>(null);
const editingText = ref(false);
const textDraft = ref("");
const resolveSourceIssues = ref(false);
const cleanupOpen = ref(false);
const sourceIssueOpen = ref(false);
const sliceOpen = ref(false);
const tabOrder = ["metadata", "evidence", "source"] as const;
const state = computed(
  () =>
    props.record.review_disposition ||
    (props.record.accepted ? "accepted" : props.record.rejected ? "rejected" : "pending"),
);
const position = computed(() => {
  const index = Number(props.record.topology_index ?? -1),
    total = Number(props.record.topology_count ?? 0);
  return index >= 0 && total > 0 ? `${index + 1} / ${total}` : "—";
});
const evidence = computed(() => Object.entries(props.record.metadata_evidence || {}));
const guidanceMatches = computed(() =>
  Object.entries(props.record.metadata_guidance_matches || {}),
);
const unresolved = computed(() =>
  Array.from(
    new Set([
      ...(props.record.metadata_incomplete_fields || []),
      ...(props.record.metadata_review_fields || []),
    ]),
  ),
);
const blocks = computed(() => props.sourceBlocks || []);
function focusables() {
  if (!dialog.value) return [] as HTMLElement[];
  return Array.from(
    dialog.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])',
    ),
  ).filter((node) => node.offsetParent !== null);
}
function handleKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && editingText.value) {
    event.preventDefault();
    saveText();
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
  tab.value = tabOrder[next];
  void nextTick(() =>
    dialog.value?.querySelector<HTMLButtonElement>(`#focus-tab-${tab.value}`)?.focus(),
  );
}
function beginTextEdit(proposal = false) {
  textDraft.value = proposal
    ? String(props.record.text_touchup_proposal?.proposed_text || props.record.text || "")
    : String(props.record.text || "");
  resolveSourceIssues.value = Boolean(props.record.source_quality_issues?.length);
  editingText.value = true;
  void nextTick(() =>
    dialog.value?.querySelector<HTMLTextAreaElement>(".focus-text-editor")?.focus(),
  );
}
function saveText() {
  if (!textDraft.value.trim()) return;
  emit("saveText", textDraft.value, resolveSourceIssues.value);
  editingText.value = false;
}
function acknowledgeSourceIssue(dontShowAgain = false) {
  if (dontShowAgain) hideSourceWarnings();
  sourceIssueOpen.value = false;
}
function preventBackgroundScroll() {
  document.documentElement.dataset.focusReview = "true";
  document.body.style.overflow = "hidden";
}
function restoreBackgroundScroll() {
  delete document.documentElement.dataset.focusReview;
  document.body.style.overflow = "";
}
onMounted(() => {
  priorActive.value = document.activeElement as HTMLElement | null;
  preventBackgroundScroll();
  textDraft.value = String(props.record.text || "");
  void nextTick(() => closeButton.value?.focus({ preventScroll: true }));
});
onBeforeUnmount(() => {
  restoreBackgroundScroll();
  priorActive.value?.focus?.({ preventScroll: true });
});
watch(
  () => props.record.record_id,
  () => {
    tab.value = "metadata";
    editingText.value = false;
    textDraft.value = String(props.record.text || "");
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
    @keydown="handleKeydown"
    :aria-labelledby="`focus-title-${record.record_id}`"
  >
    <header class="focus-head">
      <div class="focus-title-block">
        <nav
          class="focus-breadcrumb"
          :aria-label="i18n.t('pdf_corpus.focus_navigation')"
        >
          <span>{{ i18n.t("pdf_corpus.corpus_builder") }}</span
          ><span aria-hidden="true">›</span
          ><span>{{ i18n.t("pdf_corpus.record_review") }}</span
          ><span aria-hidden="true">›</span><strong>{{ record.record_id }}</strong>
        </nav>
        <div class="focus-history-controls">
          <button
            class="btn small"
            type="button"
            :disabled="!canHistoryBack"
            @click="emit('historyBack')"
          >
            ← {{ i18n.t("ui.back") }}</button
          ><button
            class="btn small"
            type="button"
            :disabled="!canHistoryForward"
            @click="emit('historyForward')"
          >
            {{ i18n.t("ui.forward") }} →</button
          ><span class="focus-nav-divider" aria-hidden="true"></span
          ><button
            class="btn small"
            type="button"
            :disabled="!canPreviousRecord"
            @click="emit('previousRecord')"
          >
            ← {{ i18n.t("pdf_corpus.previous_record") }}</button
          ><button
            class="btn small"
            type="button"
            :disabled="!canNextRecord"
            @click="emit('nextRecord')"
          >
            {{ i18n.t("pdf_corpus.next_record") }} →
          </button>
        </div>
        <span class="eyebrow">{{ i18n.t("pdf_corpus.focus_view") }}</span>
        <h2 :id="`focus-title-${record.record_id}`">{{ record.record_id }}</h2>
        <div class="focus-facts">
          <span
            ><b>{{ position }}</b> {{ i18n.t("pdf_corpus.records") }}</span
          ><span>{{ record.inline_citation }}</span
          ><span
            >{{ Number(record.text_length || String(record.text || "").length).toLocaleString() }}
            {{ i18n.t("pdf_corpus.characters") }}</span
          ><span class="state-pill" :data-state="state">{{
            i18n.t(`pdf_corpus.disposition.${state}`, state)
          }}</span
          ><span
            v-if="record.text_noise?.score != null"
            class="state-pill"
            :data-state="record.text_noise.unusable ? 'rejected' : 'pending'"
            >{{
              i18n.tf("pdf_corpus.text_noise.score", {
                score: Math.round(Number(record.text_noise.score)),
              })
            }}</span
          >
        </div>
      </div>
      <div class="focus-head-actions">
        <details class="focus-shortcuts">
          <summary :title="i18n.t('record.keyboard_shortcuts')">?</summary>
          <div class="focus-shortcuts-popover">
            <strong>{{ i18n.t("record.keyboard_shortcuts") }}</strong>
            <span
              ><kbd>Alt</kbd> + <kbd>←</kbd> / <kbd>→</kbd>
              {{ i18n.t("record.previous_next") }}</span
            >
            <span><kbd>Esc</kbd> {{ i18n.t("ui.close") }}</span>
            <span
              ><kbd>Ctrl/Cmd</kbd> + <kbd>S</kbd>
              {{ i18n.t("pdf_corpus.save_reviewed_text") }}</span
            >
          </div>
        </details>
        <button ref="closeButton" class="btn" type="button" @click="emit('close')">
          {{ i18n.t("ui.close") }}
        </button>
      </div>
    </header>
    <main class="focus-workspace">
      <article class="focus-record" aria-labelledby="focus-record-heading">
        <div class="focus-record-heading">
          <div>
            <span class="eyebrow">{{
              i18n.t("pdf_corpus.reviewed_record_text")
            }}</span>
            <h3 id="focus-record-heading">
              {{
                record.text_review_status === "human_corrected"
                  ? i18n.t("pdf_corpus.human_corrected")
                  : i18n.t("pdf_corpus.read_record")
              }}
            </h3>
          </div>
          <div class="heading-actions">
            <span v-if="unresolved.length" class="unresolved-badge"
              >{{ unresolved.length }}
              {{ i18n.t("pdf_corpus.unresolved_fields") }}</span
            ><button
              v-if="record.source_quality_issues?.length"
              class="source-warn-icon"
              type="button"
              :aria-label="i18n.t('pdf_corpus.source_warning_icon')"
              @click="sourceIssueOpen = true"
            >
              <AppIcon name="warning" /></button
            ><button class="btn" type="button" @click="emit('previewJsonl')" :disabled="busy">
              {{ i18n.t("pdf_corpus.preview_jsonl") }}</button
            ><button
              class="btn"
              type="button"
              @click="editingText ? (editingText = false) : beginTextEdit()"
              :disabled="busy"
            >
              {{
                editingText
                  ? i18n.t("ui.cancel")
                  : i18n.t("pdf_corpus.edit_text")
              }}
            </button>
          </div>
        </div>
        <p v-if="record.text_noise?.score != null" class="record-noise-summary" role="status">
          {{
            i18n.tf("pdf_corpus.text_noise.score", {
              score: Math.round(Number(record.text_noise.score)),
            })
          }}
          <span v-if="record.text_noise.unusable">
            ·
            {{
              i18n.t("pdf_corpus.text_noise.unusable")
            }}
          </span>
        </p>
        <CorpusReviewQueueContext
          :current-record-id="record.record_id"
          :just-processed-record-id="justProcessedRecordId"
          :next-record-id="nextRecordId"
          @navigate-record="emit('navigateRecord', $event)"
        />
        <div
          v-if="record.text_touchup_proposal?.status === 'pending_review'"
          class="touchup-proposal"
          role="status"
        >
          <b>{{
            i18n.t("pdf_corpus.llm_touchup_proposal_available")
          }}</b
          ><span>{{
            i18n.t("pdf_corpus.llm_touchup_proposal_help")
          }}</span
          ><button class="btn small" type="button" :disabled="busy" @click="beginTextEdit(true)">
            {{ i18n.t("pdf_corpus.review_touchup_proposal") }}
          </button>
        </div>
        <div v-if="editingText" class="focus-text-edit">
          <div class="focus-text-tools">
            <button class="btn" type="button" @click="cleanupOpen = true" :disabled="busy">
              {{ i18n.t("pdf_corpus.clean_text") }}</button
            ><button
              class="btn"
              type="button"
              @click="emit('llmTouchup', textDraft)"
              :disabled="busy"
            >
              {{ i18n.t("pdf_corpus.llm_touchup") }}
            </button>
          </div>
          <textarea
            v-model="textDraft"
            class="focus-text-editor"
            :aria-label="i18n.t('pdf_corpus.reviewed_record_text')"
          ></textarea
          ><label v-if="record.source_quality_issues?.length" class="resolve-check"
            ><input v-model="resolveSourceIssues" type="checkbox" /><span>{{
              i18n.t("pdf_corpus.resolve_source_with_correction")
            }}</span></label
          >
          <div class="edit-actions">
            <button class="btn" type="button" @click="editingText = false">
              {{ i18n.t("ui.cancel") }}</button
            ><button
              class="btn primary"
              type="button"
              @click="saveText"
              :disabled="busy || !textDraft.trim()"
            >
              {{ i18n.t("pdf_corpus.save_reviewed_text") }}
            </button>
          </div>
        </div>
        <div v-else class="focus-record-text" tabindex="-1">{{ record.text }}</div>
      </article>
      <aside class="focus-data" :aria-label="i18n.t('pdf_corpus.record_data')">
        <div
          class="tabs"
          role="tablist"
          :aria-label="i18n.t('pdf_corpus.focus_detail_tabs')"
          @keydown="handleTabKeydown"
        >
          <button
            id="focus-tab-metadata"
            type="button"
            role="tab"
            :tabindex="tab === 'metadata' ? 0 : -1"
            :aria-selected="tab === 'metadata'"
            aria-controls="focus-panel-metadata"
            @click="tab = 'metadata'"
          >
            {{ i18n.t("pdf_corpus.metadata_tab") }}</button
          ><button
            id="focus-tab-evidence"
            type="button"
            role="tab"
            :tabindex="tab === 'evidence' ? 0 : -1"
            :aria-selected="tab === 'evidence'"
            aria-controls="focus-panel-evidence"
            @click="tab = 'evidence'"
          >
            {{ i18n.t("pdf_corpus.evidence_tab") }}</button
          ><button
            id="focus-tab-source"
            type="button"
            role="tab"
            :tabindex="tab === 'source' ? 0 : -1"
            :aria-selected="tab === 'source'"
            aria-controls="focus-panel-source"
            @click="tab = 'source'"
          >
            {{ i18n.t("pdf_corpus.source_tab") }}
          </button>
        </div>
        <div
          v-if="tab === 'metadata'"
          id="focus-panel-metadata"
          class="tab-panel focus-metadata-panel"
          role="tabpanel"
          aria-labelledby="focus-tab-metadata"
        >
          <CorpusMetadataResolutionPanel
            :record="record"
            :region-types="regionTypes || []"
            :discourse-roles="discourseRoles || []"
            :busy="busy"
            :confidence-calibration="confidenceCalibration || {}"
            @resolve="(field, value) => emit('resolveMetadata', field, value)"
            @no-value="(field) => emit('confirmNoMetadataValue', field)"
            @dirty="(value) => emit('metadataDirty', value)"
            @source="tab = 'source'"
          />
        </div>
        <div
          v-else-if="tab === 'evidence'"
          id="focus-panel-evidence"
          class="tab-panel"
          role="tabpanel"
          aria-labelledby="focus-tab-evidence"
        >
          <section
            v-if="guidanceMatches.length"
            class="guidance-match-panel"
            aria-labelledby="guidance-match-title"
          >
            <h3 id="guidance-match-title">
              {{ i18n.t("pdf_corpus.run_guidance_matches") }}
            </h3>
            <p>
              {{
                i18n.t("pdf_corpus.run_guidance_matches_help")
              }}
            </p>
            <ul>
              <li v-for="[field, hits] in guidanceMatches" :key="field">
                <b>{{ i18n.t(`record.${field}`, field.replace(/_/g, " ")) }}</b>
                <span v-for="hit in hits" :key="`${hit.term}-${hit.occurrences}`"
                  >{{ hit.term }} ·
                  {{
                    i18n.tf("pdf_corpus.run_guidance_occurrences", {
                      count: hit.occurrences,
                    })
                  }}</span
                >
              </li>
            </ul>
          </section>
          <article v-for="[field, info] in evidence" :key="field" class="evidence-row">
            <header>
              <b>{{ i18n.t(`record.${field}`, field.replace(/_/g, " ")) }}</b
              ><span>{{ Math.round(Number(info.confidence || 0) * 100) }}%</span>
            </header>
            <p>
              {{
                info.reason ||
                i18n.t("pdf_corpus.no_evidence_reason")
              }}
            </p>
            <small>{{
              (info.block_ids || []).join(", ") ||
              i18n.t("pdf_corpus.no_bound_blocks")
            }}</small>
          </article>
          <p v-if="!evidence.length" class="empty-note">
            {{
              i18n.t("pdf_corpus.no_field_evidence")
            }}
          </p>
        </div>
        <div
          v-else
          id="focus-panel-source"
          class="tab-panel source-tab-panel"
          role="tabpanel"
          aria-labelledby="focus-tab-source"
        >
          <CorpusSourceSummary
            :pdf-url="sourcePdfUrl || ''"
            :page="sourcePdfPage || 1"
            :page-count="0"
            :page-width="sourcePageWidth || 0"
            :page-height="sourcePageHeight || 0"
            :blocks="blocks"
            :show-pdf-explorer="false"
            @open-viewer="emit('openSourceViewer')"
          /><CorpusSourceIssuePanel
            v-if="record.source_quality_issues?.length"
            :issues="record.source_quality_issues"
          /><CorpusSourceIssuePanel
            v-else-if="record.resolved_source_quality_issues?.length"
            :issues="record.resolved_source_quality_issues"
            :resolved="true"
          />
          <details class="focus-source-section">
            <summary>
              {{ i18n.t("pdf_corpus.boundary_second_reader") }}
            </summary>
            <CorpusBoundaryAdjudication
              :record="record"
              :can-previous="Boolean(canMergePrevious)"
              :can-next="Boolean(canMergeNext)"
              :busy="busy"
              :profiles="providerProfiles || []"
              :provider-profile-id="llmProviderProfileId || ''"
              :model-override="llmModelOverride"
              @update:provider-profile-id="(value) => emit('updateLlmProviderProfile', value)"
              @update:model-override="(value) => emit('updateLlmModel', value)"
              @adjudicate="
                (direction, profileId, model) =>
                  emit('adjudicateBoundary', direction, profileId, model)
              "
            />
          </details>
          <details class="focus-source-section">
            <summary>
              {{ i18n.t("pdf_corpus.extracted_source_text") }}
            </summary>
            <p class="empty-note">
              {{
                i18n.t("pdf_corpus.extracted_source_text_help")
              }}
            </p>
            <article v-for="block in blocks" :key="block.block_id" class="source-row">
              <header>
                <b>{{ block.block_id }}</b
                ><span>PDF {{ block.page }} · {{ block.type }}</span>
              </header>
              <p>{{ block.text }}</p>
            </article>
            <p v-if="!blocks.length" class="empty-note">
              {{
                i18n.t("pdf_corpus.source_loading_or_unavailable")
              }}
            </p>
          </details>
          <details class="focus-source-section">
            <summary>{{ i18n.t("pdf_corpus.revision_history") }}</summary>
            <CorpusRevisionHistory :record="record" />
          </details>
        </div>
      </aside>
    </main>
    <p v-if="canAccept === false" id="focus-metadata-blocker" class="focus-blocker" role="status">
      {{
        record.source_quality_issues?.length
          ? i18n.t("pdf_corpus.resolve_source_before_accept")
          : i18n.t("pdf_corpus.resolve_metadata_before_accept")
      }}
    </p>
    <footer class="focus-actions">
      <div class="structural-actions">
        <button
          class="btn"
          type="button"
          @click="emit('merge', 'previous')"
          :disabled="busy || !canMergePrevious"
        >
          {{ i18n.t("pdf_corpus.combine_previous") }}</button
        ><button
          class="btn"
          type="button"
          @click="emit('merge', 'next')"
          :disabled="busy || !canMergeNext"
        >
          {{ i18n.t("pdf_corpus.combine_next") }}</button
        ><button
          class="btn"
          type="button"
          @click="sliceOpen = true"
          :disabled="busy || editingText || (!canMergePrevious && !canMergeNext)"
        >
          {{ i18n.t("pdf_corpus.slice_record") }}</button
        ><button class="btn" type="button" @click="emit('undo')" :disabled="busy">
          {{ i18n.t("pdf_corpus.undo") }}</button
        ><button class="btn" type="button" @click="emit('redo')" :disabled="busy">
          {{ i18n.t("pdf_corpus.redo") }}
        </button>
      </div>
      <div class="decision-actions">
        <button class="btn" type="button" @click="emit('requeueMetadata')" :disabled="busy">
          {{ i18n.t("pdf_corpus.requeue_metadata") }}</button
        ><button class="btn" type="button" @click="emit('skip')" :disabled="busy">
          {{ i18n.t("pdf_corpus.skip") }}</button
        ><button class="btn danger" type="button" @click="emit('reject')" :disabled="busy">
          {{ i18n.t("pdf_corpus.reject_next") }}</button
        ><button
          class="btn primary"
          type="button"
          @click="emit('accept')"
          :disabled="busy || canAccept === false"
          :aria-describedby="canAccept === false ? 'focus-metadata-blocker' : undefined"
        >
          {{ i18n.t("pdf_corpus.accept_next") }}
        </button>
      </div>
    </footer>
    <CorpusBoundarySliceDialog
      v-if="sliceOpen"
      :text="String(record.text || '')"
      :can-previous="Boolean(canMergePrevious)"
      :can-next="Boolean(canMergeNext)"
      :busy="busy"
      @close="sliceOpen = false"
      @slice="
        (direction, offset, keepEnd) => {
          emit('slice', direction, offset, keepEnd);
          sliceOpen = false;
        }
      "
    />
    <CorpusTextCleanupDialog
      v-if="cleanupOpen"
      :text="textDraft"
      :recurring-lines="recurringLines || []"
      :document-terms="documentTerms || []"
      @close="cleanupOpen = false"
      @apply="
        (value) => {
          textDraft = value;
          cleanupOpen = false;
        }
      "
    />
    <CorpusSourceQualityDialog
      :open="sourceIssueOpen && Boolean(record.source_quality_issues?.length)"
      :issues="record.source_quality_issues"
      @close="acknowledgeSourceIssue"
      @edit-text="
        sourceIssueOpen = false;
        beginTextEdit();
      "
      @open-source="
        sourceIssueOpen = false;
        tab = 'source';
      "
    />
  </section>
</template>

<style scoped>
.touchup-proposal {
  display: grid;
  gap: 5px;
  max-width: 86ch;
  margin: 18px auto 0;
  padding: 11px 12px;
  border: 1px solid var(--tone-info-border);
  border-radius: 9px;
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
}
.touchup-proposal span {
  font-size: 0.8125rem;
}
.touchup-proposal .btn {
  justify-self: start;
}
.focus-review {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: var(--bg);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  color: var(--text);
}
.focus-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  padding: 18px clamp(18px, 3vw, 42px);
  border-bottom: 1px solid var(--line);
  background: var(--card);
}
.focus-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
}
.focus-shortcuts {
  position: relative;
}
.focus-shortcuts summary {
  list-style: none;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  cursor: pointer;
  font-weight: 900;
}
.focus-shortcuts summary::-webkit-details-marker {
  display: none;
}
.focus-shortcuts-popover {
  position: absolute;
  right: 0;
  top: 46px;
  z-index: 20;
  width: 270px;
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  box-shadow: var(--shadow-overlay);
  font-size: 0.75rem;
}
.focus-shortcuts-popover span {
  color: var(--muted);
}
kbd {
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--soft);
  padding: 1px 4px;
  font: inherit;
}
.focus-title-block {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.focus-breadcrumb {
  display: flex;
  gap: 7px;
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.8125rem;
  color: var(--muted);
}
.focus-breadcrumb strong {
  color: var(--text);
}
.focus-history-controls {
  display: flex;
  gap: 7px;
  align-items: center;
  flex-wrap: wrap;
  margin: 2px 0 4px;
}
.focus-nav-divider {
  width: 1px;
  height: 24px;
  background: var(--line);
  margin-inline: 2px;
}
.focus-head h2 {
  margin: 0;
  font-size: 1.375rem;
  overflow-wrap: anywhere;
}
.eyebrow {
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  font-weight: 800;
}
.focus-facts {
  display: flex;
  gap: 14px;
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.8125rem;
  color: var(--muted);
}
.state-pill,
.unresolved-badge {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 0.8125rem;
  font-weight: 750;
}
.state-pill[data-state="accepted"] {
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
}
.state-pill[data-state="rejected"] {
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.focus-workspace {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(370px, 440px);
  overflow: hidden;
}
.focus-record {
  min-width: 0;
  min-height: 0;
  overflow: auto;
  border-inline-end: 1px solid var(--line);
  background: var(--card);
}
.focus-record-heading {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--card);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px clamp(22px, 4vw, 54px);
  border-bottom: 1px solid var(--line);
}
.focus-record-heading h3 {
  margin: 3px 0 0;
  font-size: 1rem;
}
.record-noise-summary {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.heading-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.source-warn-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  margin: 0;
  padding: 0;
  border: 1px solid var(--tone-warn-border);
  border-radius: 10px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  cursor: pointer;
}
.source-warn-icon svg {
  width: 18px;
  height: 18px;
}
.unresolved-badge {
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.focus-record-text {
  max-width: 78ch;
  margin: 0 auto;
  padding: 34px clamp(24px, 5vw, 72px) 80px;
  white-space: pre-wrap;
  font:
    18px/1.78 Georgia,
    serif;
  outline: none;
}
.focus-text-tools {
  display: flex;
  justify-content: flex-end;
}
.focus-text-edit {
  max-width: 90ch;
  margin: 24px auto;
  padding: 0 clamp(24px, 4vw, 54px);
  display: grid;
  gap: 12px;
}
.focus-text-editor {
  width: 100%;
  min-height: 58vh;
  resize: vertical;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--bg);
  color: var(--text);
  font:
    17px/1.7 Georgia,
    serif;
}
.resolve-check {
  display: flex;
  gap: 9px;
  align-items: flex-start;
  font-size: 0.8125rem;
  line-height: 1.5;
}
.resolve-check input {
  inline-size: 18px;
  block-size: 18px;
  flex: none;
}
.edit-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.focus-data {
  min-width: 0;
  min-height: 0;
  overflow: auto;
  background: var(--soft);
}
.tabs {
  position: sticky;
  top: 0;
  z-index: 3;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  background: var(--card);
  border-bottom: 1px solid var(--line);
}
.tabs button {
  min-height: 48px;
  border: 0;
  border-inline-end: 1px solid var(--line);
  background: transparent;
  color: inherit;
  font-size: 0.8125rem;
  font-weight: 750;
  cursor: pointer;
}
.tabs button[aria-selected="true"] {
  box-shadow: inset 0 -3px 0 var(--accent);
  background: var(--soft);
}
.tab-panel {
  padding: 16px;
  display: grid;
  gap: 12px;
}
.focus-metadata-panel {
  padding: 0;
}
.focus-metadata-panel :deep(.metadata-review) {
  border: 0;
  border-radius: 0;
}
.guidance-match-panel {
  display: grid;
  gap: 6px;
  border: 1px solid var(--ui-accent-border);
  border-radius: 9px;
  background: var(--ui-accent-soft);
  padding: 11px;
}
.guidance-match-panel h3,
.guidance-match-panel p {
  margin: 0;
}
.guidance-match-panel h3 {
  color: var(--text);
  font-size: 0.875rem;
}
.guidance-match-panel p,
.guidance-match-panel li {
  color: var(--text-2);
  font-size: 0.8125rem;
  line-height: 1.5;
}
.guidance-match-panel ul {
  display: grid;
  gap: 5px;
  margin: 0;
  padding-inline-start: 18px;
}
.guidance-match-panel li span {
  margin-inline-start: 8px;
}
.evidence-row,
.source-row {
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  padding: 11px;
}
.evidence-row header,
.source-row header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.8125rem;
}
.evidence-row p {
  margin: 7px 0;
  font-size: 0.8125rem;
  line-height: 1.5;
}
.evidence-row small {
  font-size: 0.8125rem;
  color: var(--muted);
}
.focus-pdf-source {
  display: grid;
  gap: 8px;
}
.focus-pdf-source {
  min-width: 0;
}
.focus-pdf-source header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  font-size: 0.875rem;
  flex-wrap: wrap;
}
.focus-pdf-source header > div {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.focus-pdf-source header span,
.focus-pdf-source p {
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.focus-pdf-source p {
  margin: 0;
  overflow-wrap: anywhere;
}
.source-row p {
  white-space: pre-wrap;
  margin: 8px 0 0;
  font:
    14px/1.6 Georgia,
    serif;
}
.source-row header span {
  font-size: 0.8125rem;
  color: var(--muted);
}
.empty-note {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.5;
}
.focus-blocker {
  margin: 0;
  padding: 10px 18px;
  border-top: 1px solid var(--tone-warn-edge);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
}
.focus-actions {
  position: fixed;
  inset-inline: var(--sidebar) 0;
  inset-block-end: 0;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 12px clamp(18px, 3vw, 42px);
  border-top: 1px solid var(--line);
  background: var(--card);
  box-shadow: 0 -0.75rem 2rem color-mix(in srgb, var(--text) 12%, transparent);
  padding-bottom: calc(12px + env(safe-area-inset-bottom));
}
.focus-review {
  padding-bottom: 5.5rem;
}
.structural-actions,
.decision-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.danger {
  border-color: var(--tone-danger-border);
  color: var(--tone-danger-fg);
}
.focus-review :is(button, [tabindex], textarea, input):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 900px) {
  .focus-workspace {
    grid-template-columns: 1fr;
    overflow: auto;
  }
  .focus-record {
    overflow: visible;
    border-inline-end: 0;
  }
  .focus-data {
    overflow: visible;
    border-top: 1px solid var(--line);
  }
  .focus-actions {
    inset-inline-start: 0;
    align-items: stretch;
    flex-direction: column;
    box-shadow: 0 -8px 24px color-mix(in srgb, var(--text) 10%, transparent);
  }
  .decision-actions {
    justify-content: flex-end;
  }
  .focus-record-text {
    font-size: 1.0625rem;
    padding: 24px 18px 50px;
  }
}
.source-tab-panel {
  min-width: 0;
  overflow-x: hidden;
}
.focus-source-section {
  min-width: 0;
  border-top: 1px solid var(--line);
}
.focus-source-section > summary {
  min-height: 44px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  font-weight: 800;
  cursor: pointer;
}
.focus-source-section :deep(.boundary-adjudication) {
  border: 0;
  border-radius: 0;
}
.source-row {
  min-width: 0;
}
.source-row p,
.source-row header {
  overflow-wrap: anywhere;
}
.source-row pre {
  max-width: 100%;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
@media (prefers-reduced-motion: reduce) {
  * {
    scroll-behavior: auto !important;
  }
}
</style>
