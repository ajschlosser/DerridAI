<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusRecord, SourceBlock } from "../api/pdfCorpus";
import type { MetadataSchema } from "../api/metadataSchemas";
import type { ProviderProfile } from "../api/system";
import CorpusSourceIssuePanel from "./CorpusSourceIssuePanel.vue";
import CorpusMetadataResolutionPanel from "./CorpusMetadataResolutionPanel.vue";
import CorpusRevisionHistory from "./CorpusRevisionHistory.vue";
import CorpusBoundaryAdjudication from "./CorpusBoundaryAdjudication.vue";
import CorpusSourceSummary from "./CorpusSourceSummary.vue";
import FieldEvidenceList from "./FieldEvidenceList.vue";
import CorpusReviewQueueContext from "./CorpusReviewQueueContext.vue";
import AppIcon from "./AppIcon.vue";

const props = defineProps<{
  record: CorpusRecord;
  schema?: MetadataSchema | null;
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
  selectedEvidenceField?: string;
  evidenceBlockIds?: string[];
  editingText?: boolean;
  textDraft?: string;
  resolveSourceIssues?: boolean;
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
  requestSlice: [];
  openSourceIssue: [];
  merge: [direction: "previous" | "next"];
  adjudicateBoundary: [direction: "previous" | "next", providerProfileId: string, model: string];
  openSourceViewer: [];
  updateLlmProviderProfile: [value: string];
  updateLlmModel: [value: string];
  beginTextEdit: [proposal?: boolean];
  cancelTextEdit: [];
  saveText: [];
  textDraftChange: [value: string];
  resolveSourceIssuesChange: [value: boolean];
  openTextCleanup: [];
  resolveMetadata: [field: string, value: unknown];
  resolveMetadataMany: [changes: Record<string, unknown>];
  confirmNoMetadataValue: [field: string];
  metadataDirty: [dirty: boolean];
  previewJsonl: [];
  llmTouchup: [text: string];
  navigateRecord: [recordId: string];
  selectEvidence: [field: string];
  toggleEvidence: [blockId: string];
  assignEvidence: [field: string, blockId: string];
}>();
const i18n = useI18nStore();
const dialog = ref<HTMLElement | null>(null);
const closeButton = ref<HTMLButtonElement | null>(null);
const tab = ref<"metadata" | "evidence" | "source">("metadata");
const priorActive = ref<HTMLElement | null>(null);
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
function requestBeginTextEdit(proposal = false) {
  emit("beginTextEdit", proposal);
}
function requestSaveText() {
  if (!String(props.textDraft || "").trim()) return;
  emit("saveText");
}
function updateTextDraft(event: Event) {
  emit("textDraftChange", (event.target as HTMLTextAreaElement).value);
}
function updateResolveSourceIssues(event: Event) {
  emit("resolveSourceIssuesChange", (event.target as HTMLInputElement).checked);
}
function openFieldEvidence(field: string) {
  emit("selectEvidence", field);
  tab.value = "evidence";
}
function normalizedWords(value: string) {
  return new Set(
    value
      .toLocaleLowerCase()
      .split(/[^\p{L}\p{N}]+/u)
      .map((item) => item.trim())
      .filter((item) => item.length > 2),
  );
}
function nearestEvidenceBlock(selectedText: string): SourceBlock | null {
  const selected = selectedText.replace(/\s+/g, " ").trim().toLocaleLowerCase();
  if (!selected) return null;
  const exact = blocks.value.find((block) =>
    String(block.text || "")
      .replace(/\s+/g, " ")
      .toLocaleLowerCase()
      .includes(selected),
  );
  if (exact) return exact;
  const wanted = normalizedWords(selected);
  if (!wanted.size) return null;
  let best: SourceBlock | null = null;
  let bestScore = 0;
  for (const block of blocks.value) {
    const words = normalizedWords(String(block.text || ""));
    const overlap = [...wanted].filter((word) => words.has(word)).length;
    const score = overlap / wanted.size;
    if (score > bestScore) {
      best = block;
      bestScore = score;
    }
  }
  return bestScore >= 0.45 ? best : null;
}
function assignSelectedEvidence(field: string, selectedText: string) {
  const block = nearestEvidenceBlock(selectedText);
  if (!block?.block_id) {
    openFieldEvidence(field);
    return;
  }
  emit("selectEvidence", field);
  emit("assignEvidence", field, String(block.block_id));
  tab.value = "evidence";
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
        <nav class="focus-breadcrumb" :aria-label="i18n.t('pdf_corpus.focus_navigation')">
          <span>{{ i18n.t("pdf_corpus.corpus_builder") }}</span
          ><span aria-hidden="true">›</span><span>{{ i18n.t("pdf_corpus.record_review") }}</span
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
            <span class="eyebrow">{{ i18n.t("pdf_corpus.reviewed_record_text") }}</span>
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
              >{{ unresolved.length }} {{ i18n.t("pdf_corpus.unresolved_fields") }}</span
            ><button
              v-if="record.source_quality_issues?.length"
              class="source-warn-icon"
              type="button"
              :aria-label="i18n.t('pdf_corpus.source_warning_icon')"
              @click="emit('openSourceIssue')"
            >
              <AppIcon name="warning" /></button
            ><button class="btn" type="button" @click="emit('previewJsonl')" :disabled="busy">
              {{ i18n.t("pdf_corpus.preview_jsonl") }}</button
            ><button
              class="btn"
              type="button"
              @click="editingText ? emit('cancelTextEdit') : requestBeginTextEdit()"
              :disabled="busy"
            >
              {{ editingText ? i18n.t("ui.cancel") : i18n.t("pdf_corpus.edit_text") }}
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
            {{ i18n.t("pdf_corpus.text_noise.unusable") }}
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
          <b>{{ i18n.t("pdf_corpus.llm_touchup_proposal_available") }}</b
          ><span>{{ i18n.t("pdf_corpus.llm_touchup_proposal_help") }}</span
          ><button
            class="btn small"
            type="button"
            :disabled="busy"
            @click="requestBeginTextEdit(true)"
          >
            {{ i18n.t("pdf_corpus.review_touchup_proposal") }}
          </button>
        </div>
        <div v-if="editingText" class="focus-text-edit">
          <div class="focus-text-tools">
            <button class="btn" type="button" @click="emit('openTextCleanup')" :disabled="busy">
              {{ i18n.t("pdf_corpus.clean_text") }}</button
            ><button
              class="btn"
              type="button"
              @click="emit('llmTouchup', textDraft || '')"
              :disabled="busy"
            >
              {{ i18n.t("pdf_corpus.llm_touchup") }}
            </button>
          </div>
          <textarea
            :value="textDraft || ''"
            @input="updateTextDraft"
            class="focus-text-editor"
            :aria-label="i18n.t('pdf_corpus.reviewed_record_text')"
          ></textarea
          ><label v-if="record.source_quality_issues?.length" class="resolve-check"
            ><input
              :checked="resolveSourceIssues"
              type="checkbox"
              @change="updateResolveSourceIssues"
            /><span>{{ i18n.t("pdf_corpus.resolve_source_with_correction") }}</span></label
          >
          <div class="edit-actions">
            <button class="btn" type="button" @click="emit('cancelTextEdit')">
              {{ i18n.t("ui.cancel") }}</button
            ><button
              class="btn primary"
              type="button"
              @click="requestSaveText"
              :disabled="busy || !String(textDraft || '').trim()"
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
            :schema="schema"
            :record="record"
            :region-types="regionTypes || []"
            :discourse-roles="discourseRoles || []"
            :busy="busy"
            :confidence-calibration="confidenceCalibration || {}"
            @resolve="(field, value) => emit('resolveMetadata', field, value)"
            @resolve-many="(changes) => emit('resolveMetadataMany', changes)"
            @no-value="(field) => emit('confirmNoMetadataValue', field)"
            @dirty="(value) => emit('metadataDirty', value)"
            @source="openFieldEvidence($event)"
            @selection-evidence="assignSelectedEvidence"
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
              {{ i18n.t("pdf_corpus.run_guidance_matches_help") }}
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
          <div class="evidence-assignment">
            <h3>{{ i18n.t("pdf_corpus.evidence_assignment_title", "Evidence for metadata") }}</h3>
            <p class="empty-note">
              {{
                i18n.t(
                  "pdf_corpus.evidence_assignment_help",
                  "Choose a metadata field, then add or remove the source spans that directly support its value. Human-selected evidence becomes reviewed provenance and can support evidence-bound metadata exemplars.",
                )
              }}
            </p>
            <FieldEvidenceList
              :evidence="record.metadata_evidence || {}"
              :selected-field="selectedEvidenceField || ''"
              @select="emit('selectEvidence', $event)"
            />
            <div v-if="selectedEvidenceField" class="evidence-source-list">
              <article
                v-for="block in blocks"
                :key="block.block_id"
                class="evidence-row evidence-source-block"
                :class="{ selected: (evidenceBlockIds || []).includes(String(block.block_id)) }"
              >
                <header>
                  <b>{{ block.block_id }}</b>
                  <span>{{ block.page ? `p. ${block.page}` : block.type }}</span>
                </header>
                <p>{{ block.text }}</p>
                <button
                  type="button"
                  class="btn small"
                  :aria-pressed="(evidenceBlockIds || []).includes(String(block.block_id))"
                  :disabled="busy"
                  @click="emit('toggleEvidence', String(block.block_id))"
                >
                  {{
                    (evidenceBlockIds || []).includes(String(block.block_id))
                      ? i18n.t("pdf_corpus.remove_evidence")
                      : i18n.t("pdf_corpus.add_evidence")
                  }}
                </button>
              </article>
            </div>
          </div>
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
              {{ i18n.t("pdf_corpus.extracted_source_text_help") }}
            </p>
            <article v-for="block in blocks" :key="block.block_id" class="source-row">
              <header>
                <b>{{ block.block_id }}</b
                ><span>PDF {{ block.page }} · {{ block.type }}</span>
              </header>
              <p>{{ block.text }}</p>
            </article>
            <p v-if="!blocks.length" class="empty-note">
              {{ i18n.t("pdf_corpus.source_loading_or_unavailable") }}
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
          @click="emit('requestSlice')"
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
  </section>
</template>

<style scoped src="../features/corpus-builder/CorpusRecordFocusReview.css"></style>
