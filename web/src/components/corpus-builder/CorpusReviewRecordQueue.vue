<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import UiButton from "../ui/UiButton.vue";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import type { ReviewQueue } from "../../types/corpus";
import type { CorpusQueueRow } from "../../features/corpus-builder/api/reviewReads";
import { rowHasSourceWarning } from "../../features/corpus-builder/domain/queueRows";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  /** Lightweight queue rows (never full Records). */
  rows: CorpusQueueRow[];
  recordTotal: number;
  selectedRecordId: string;
  selectedReviewIds: Set<string>;
  allVisibleSelected: boolean;
  loading: boolean;
  hydrated: boolean;
  queue?: ReviewQueue;
  searching?: boolean;
  canOpenPublish?: boolean;
  disabled?: boolean;
  pageNumber?: number;
  pageCount?: number;
  hasPreviousPage?: boolean;
  hasNextPage?: boolean;
  activeProcessingRecordIds?: Set<string>;
}>();

const emit = defineEmits<{
  rootChange: [element: HTMLElement | null];
  collapse: [];
  toggleVisible: [selected: boolean];
  toggleRecord: [recordId: string, selected: boolean];
  selectRecord: [row: CorpusQueueRow];
  sourceWarning: [row: CorpusQueueRow];
  showAll: [];
  openPublish: [];
  previousPage: [];
  nextPage: [];
}>();

const i18n = useI18nStore();
const queueRoot = ref<HTMLElement | null>(null);
const llmProcessedHelp = i18n.t(
  "pdf_corpus.llm_processed_help",
  "The metadata enrichment run finished for this record; it is now waiting for human review.",
);

const completedQueue = computed(() => {
  if (props.searching || props.rows.length) return "";
  if (props.queue === "ready") return "ready";
  if (["issues", "metadata", "topology", "source"].includes(String(props.queue || "")))
    return "issues";
  return "";
});

onMounted(() => emit("rootChange", queueRoot.value));
onBeforeUnmount(() => emit("rootChange", null));

/**
 * What tells one row from the next. A citation is the same for every record of a work, so the row leads with where
 * the record sits (its pages) and the opening of its own text.
 */
function locator(record: CorpusQueueRow) {
  const start = record.page_start,
    end = record.page_end;
  if (start == null || start === "") return "";
  const pages = end != null && end !== "" && end !== start ? `${start}–${end}` : String(start);
  return `${i18n.t("pdf_corpus.page_abbrev")} ${pages}`;
}
/** A long build-prefixed ID wraps over several lines; the trailing sequence number is what tells rows apart. */
function shortRecordId(recordId: string) {
  const match = /^.+?[-_.:](\d+)$/.exec(recordId);
  return match ? `#${Number(match[1])}` : recordId;
}
function isActivelyEnriching(record: CorpusQueueRow) {
  return (
    record.review_state === "preparing" &&
    Boolean(props.activeProcessingRecordIds?.has(record.record_id))
  );
}
function displayRecordState(record: CorpusQueueRow) {
  return isActivelyEnriching(record) ? "enriching" : record.review_state || "ready";
}
function recordStateLabel(record: CorpusQueueRow) {
  if (isActivelyEnriching(record)) {
    return i18n.t("pdf_corpus.record_state.enriching", "Enriching");
  }
  const state = record.review_state || "ready";
  if (state === "preparing") {
    return i18n.t("pdf_corpus.record_state.preparing", "Preparing");
  }
  return i18n.t(
    `pdf_corpus.record_state.${state}`,
    state === "ready" ? "Ready" : state.replace(/_/g, " "),
  );
}

// A shape as well as a colour, so state never depends on colour alone (WCAG 1.4.1).
function recordStateIcon(record: CorpusQueueRow) {
  const state = record.review_state;
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

function extraIssueKinds(record: CorpusQueueRow) {
  return record.review_issue_codes.filter((kind: string) => kind !== record.review_state);
}

function visibleSelectionChanged(event: Event) {
  emit("toggleVisible", (event.target as HTMLInputElement).checked);
}

function recordSelectionChanged(recordId: string, event: Event) {
  emit("toggleRecord", recordId, (event.target as HTMLInputElement).checked);
}
</script>

<template>
  <nav ref="queueRoot" class="records-pane" tabindex="-1" aria-labelledby="pdf-corpus-records-pane">
    <div class="pane-head">
      <b id="pdf-corpus-records-pane">{{ i18n.t("pdf_corpus.review_queue") }}</b>
      <button
        type="button"
        class="link-button queue-toggle"
        :title="i18n.t('pdf_corpus.hide_queue')"
        @click="emit('collapse')"
      >
        <span aria-hidden="true">«</span>
        <span class="sr-only">{{ i18n.t("pdf_corpus.hide_queue") }}</span>
      </button>
      <label class="select-visible">
        <input
          type="checkbox"
          :checked="props.allVisibleSelected"
          :disabled="!props.rows.length || props.disabled"
          @change="visibleSelectionChanged"
        />
        <span>{{ i18n.t("pdf_corpus.select_visible") }}</span>
      </label>
      <span>{{ props.recordTotal }}</span>
    </div>

    <div v-for="record in props.rows" :key="record.record_id" class="record-row-wrap">
      <label class="record-select">
        <input
          type="checkbox"
          :checked="props.selectedReviewIds.has(record.record_id)"
          :aria-label="
            i18n.tf('pdf_corpus.select_record_id', {
              record: record.record_id,
            })
          "
          @change="recordSelectionChanged(record.record_id, $event)"
        />
        <span class="sr-only">{{
          i18n.tf("pdf_corpus.select_record_id", {
            record: record.record_id,
          })
        }}</span>
      </label>

      <button
        type="button"
        class="record-row"
        :class="{ active: record.record_id === props.selectedRecordId }"
        :aria-current="record.record_id === props.selectedRecordId ? 'true' : undefined"
        @click="emit('selectRecord', record)"
      >
        <span class="record-state-icon" :data-state="displayRecordState(record)" aria-hidden="true">
          <span v-if="isActivelyEnriching(record)" class="spinner record-processing-spinner"></span>
          <AppIcon v-else-if="recordStateIcon(record)" :name="recordStateIcon(record)" />
        </span>
        <span class="record-row-main">
          <span class="record-row-head">
            <b :title="record.record_id">
              <span aria-hidden="true">{{ shortRecordId(record.record_id) }}</span>
              <span class="sr-only">{{ record.record_id }}</span>
            </b>
            <small v-if="locator(record)">{{ locator(record) }}</small>
            <span class="record-row-status" :data-state="displayRecordState(record)">
              {{ recordStateLabel(record) }}
            </span>
          </span>
          <span v-if="record.text_preview" class="record-row-snippet">{{
            record.text_preview
          }}</span>
          <small class="record-row-length">
            {{ record.text_length.toLocaleString() }} {{ i18n.t("pdf_corpus.characters") }}
          </small>
          <UiTooltip
            v-if="record.metadata_llm_processed"
            :text="llmProcessedHelp"
            trigger-mode="content"
            placement="bottom"
          >
            <span
              class="record-llm-processed"
              role="img"
              :aria-label="i18n.t('pdf_corpus.llm_processed', 'LLM processed')"
            >
              <AppIcon name="spark" />
            </span>
          </UiTooltip>
          <small v-if="extraIssueKinds(record).length" class="record-issue-summary">
            {{
              extraIssueKinds(record)
                .map((kind) => i18n.t(`pdf_corpus.record_state.${kind}`, kind))
                .join(" · ")
            }}
          </small>
        </span>
      </button>

      <button
        v-if="rowHasSourceWarning(record)"
        type="button"
        class="record-source-warn"
        :aria-label="i18n.t('pdf_corpus.source_warning_icon')"
        @click.stop="emit('sourceWarning', record)"
      >
        <AppIcon name="warning" />
      </button>
    </div>

    <div v-if="props.loading && !props.hydrated" class="rail-empty" role="status">
      {{ i18n.t("pdf_corpus.loading_records") }}
    </div>
    <div
      v-else-if="!props.rows.length"
      class="rail-empty"
      :data-complete="completedQueue || undefined"
      role="status"
    >
      <span v-if="completedQueue" class="rail-empty-icon" aria-hidden="true">
        <AppIcon name="check" />
      </span>
      <b v-if="completedQueue === 'ready'">{{ i18n.t("pdf_corpus.queue_empty_ready_title") }}</b>
      <b v-else-if="completedQueue === 'issues'">{{
        i18n.t("pdf_corpus.queue_empty_issues_title")
      }}</b>
      <span v-else>{{ i18n.t("pdf_corpus.no_records_filter") }}</span>
      <small v-if="completedQueue">{{ i18n.t("pdf_corpus.queue_empty_complete_help") }}</small>
      <span class="rail-empty-actions">
        <UiButton size="small" @click="emit('showAll')">
          {{ i18n.t("pdf_corpus.show_all_records") }}
        </UiButton>
        <UiButton
          v-if="completedQueue && props.canOpenPublish"
          size="small"
          variant="primary"
          :label="i18n.t('pdf_corpus.primary_status.publication_readiness')"
          @click="emit('openPublish')"
        />
      </span>
    </div>
    <div
      v-if="(props.pageCount ?? 1) > 1"
      class="pager"
      role="group"
      :aria-label="i18n.t('pdf_corpus.queue_paging')"
    >
      <UiButton
        size="small"
        icon-only
        :label="i18n.t('ui.previous')"
        :disabled="!props.hasPreviousPage"
        @click="emit('previousPage')"
      >
        <template #icon-label><span aria-hidden="true">‹</span></template>
      </UiButton>
      <span>{{ props.pageNumber }} / {{ props.pageCount }}</span>
      <UiButton
        size="small"
        icon-only
        :label="i18n.t('ui.next')"
        :disabled="!props.hasNextPage"
        @click="emit('nextPage')"
      >
        <template #icon-label><span aria-hidden="true">›</span></template>
      </UiButton>
    </div>
  </nav>
</template>

<style scoped>
/* Paging belongs to the list it pages, pinned under the rows. */
.pager {
  position: sticky;
  bottom: 0;
  z-index: 4;
  display: flex;
  gap: var(--space-2);
  align-items: center;
  justify-content: center;
  padding: 0.375rem 0.5rem;
  border-top: 1px solid var(--border-subtle);
  background: var(--surface-subtle);
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
.record-row-snippet {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  color: var(--text-secondary, var(--text-secondary));
  font-size: 0.8125rem;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.records-pane {
  background: var(--surface-subtle);
  border-inline-end: 1px solid var(--border-subtle);
}
.pane-head {
  position: sticky;
  top: 0;
  z-index: 4;
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto auto;
  grid-template-areas: "select title count hide";
  align-items: center;
  gap: 0.25rem 0.5rem;
  min-height: 0;
  padding: 0.375rem 0.5rem 0.375rem 0;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-subtle);
  font-size: 0.8125rem;
}
.pane-head > b {
  grid-area: title;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pane-head > span {
  grid-area: count;
}
.pane-head > .select-visible {
  grid-area: select;
}
.pane-head > .queue-toggle {
  grid-area: hide;
  justify-self: end;
}
.queue-toggle {
  font-size: 0.8125rem;
}
/* A single header row: the select-all box lines up with the row boxes below; its words are for assistive technology. */
.select-visible span {
  position: absolute;
  inline-size: 1px;
  block-size: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}
.select-visible {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 1.5rem;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 650;
  cursor: pointer;
}
.select-visible input,
.record-select input {
  inline-size: 18px;
  block-size: 18px;
  accent-color: var(--ui-accent);
}
.record-row-wrap {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  align-items: stretch;
  border-bottom: 1px solid var(--border-subtle);
}
.record-select {
  display: grid;
  place-items: center;
  min-width: 32px;
  cursor: pointer;
}
.record-row {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr);
  align-items: start;
  gap: 0.5rem;
  width: 100%;
  min-height: 0;
  padding: 0.5rem 0.5rem 0.5rem 0.25rem;
  border: 0;
  background: transparent;
  text-align: start;
  cursor: pointer;
}
.record-row:hover {
  background: var(--surface-hover);
}
.record-row:focus-visible {
  position: relative;
  z-index: 1;
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: -3px;
}
.record-row.active {
  background: var(--surface-selected);
  box-shadow: inset 3px 0 0 var(--ui-accent);
}
.record-row-wrap .record-row {
  border-bottom: 0;
}
.record-row b,
.record-row small {
  font-size: 0.8125rem;
}
.record-row small {
  color: var(--text-secondary);
  line-height: 1.35;
}
.record-row-main {
  display: grid;
  gap: 0.125rem;
  min-width: 0;
}
.record-row-main b {
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
}
.record-state-icon {
  display: grid;
  place-items: center;
  inline-size: 1.25rem;
  block-size: 1.25rem;
  margin-block-start: 0.0625rem;
  box-sizing: border-box;
  border: 2px solid var(--text-secondary);
  border-radius: 50%;
  color: var(--text-secondary);
}
.record-state-icon svg {
  inline-size: 0.75rem;
  block-size: 0.75rem;
}
.record-state-icon[data-state="enriching"] {
  border-color: transparent;
}
.record-processing-spinner {
  inline-size: 0.9rem;
  block-size: 0.9rem;
  margin: 0;
  border-width: 2px;
  border-color: var(--border-subtle);
  border-top-color: var(--ui-accent);
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
.record-row-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.125rem 0.5rem;
  min-width: 0;
}
.record-row-length {
  font-variant-numeric: tabular-nums;
}
.record-row-status {
  display: inline-flex;
  width: max-content;
  margin-inline-start: auto;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--surface-subtle);
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
.record-llm-processed {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  margin-top: 4px;
  color: var(--tone-ok-fg);
}
.record-llm-processed svg {
  width: 13px;
  height: 13px;
}
.record-issue-summary {
  margin-top: 3px;
  color: var(--text-secondary);
}
.record-source-warn {
  display: grid;
  place-items: center;
  min-width: 36px;
  min-height: 36px;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--tone-warn-fg);
  cursor: pointer;
}
.record-source-warn:focus-visible {
  outline: 3px solid var(--ui-accent);
  outline-offset: 2px;
}
.record-source-warn svg {
  width: 18px;
  height: 18px;
}
.rail-empty {
  display: grid;
  gap: var(--space-2);
  justify-items: start;
  padding: 18px 14px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.rail-empty[data-complete] {
  color: var(--text-primary);
}
.rail-empty-icon {
  display: grid;
  width: 1.75rem;
  height: 1.75rem;
  place-items: center;
  border: 1px solid var(--tone-ok-border);
  border-radius: 999px;
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
}
.rail-empty-icon svg {
  width: 1rem;
  height: 1rem;
}
.rail-empty small {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}
.rail-empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
