<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
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
  disabled?: boolean;
}>();

const emit = defineEmits<{
  rootChange: [element: HTMLElement | null];
  collapse: [];
  toggleVisible: [selected: boolean];
  toggleRecord: [recordId: string, selected: boolean];
  selectRecord: [row: CorpusQueueRow];
  sourceWarning: [row: CorpusQueueRow];
  showAll: [];
}>();

const i18n = useI18nStore();
const queueRoot = ref<HTMLElement | null>(null);
const llmProcessedHelp = i18n.t(
  "pdf_corpus.llm_processed_help",
  "The metadata enrichment run finished for this record; it is now waiting for human review.",
);

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
function recordStateLabel(record: CorpusQueueRow) {
  const state = record.review_state || "ready";
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
      <button type="button" class="link-button queue-toggle" @click="emit('collapse')">
        {{ i18n.t("pdf_corpus.hide_queue") }}
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
        <span class="record-state-icon" :data-state="record.review_state" aria-hidden="true">
          <AppIcon v-if="recordStateIcon(record)" :name="recordStateIcon(record)" />
        </span>
        <span class="record-row-main">
          <b>{{ record.record_id }}</b>
          <small>
            <template v-if="locator(record)">{{ locator(record) }} · </template
            >{{ record.text_length.toLocaleString() }} {{ i18n.t("pdf_corpus.characters") }}
          </small>
          <span v-if="record.text_preview" class="record-row-snippet">{{
            record.text_preview
          }}</span>
          <span class="record-row-status" :data-state="record.review_state">
            {{ recordStateLabel(record) }}
          </span>
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
    <div v-else-if="!props.rows.length" class="rail-empty">
      {{ i18n.t("pdf_corpus.no_records_filter") }}
      <button type="button" class="btn small" @click="emit('showAll')">
        {{ i18n.t("pdf_corpus.show_all_records") }}
      </button>
    </div>
  </nav>
</template>

<style scoped>
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
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas: "title count" "select hide";
  align-items: center;
  gap: 0.25rem 0.5rem;
  min-height: 0;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-subtle);
  font-size: 0.8125rem;
}
.pane-head > b {
  grid-area: title;
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
.select-visible {
  display: inline-flex;
  align-items: center;
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
  grid-template-columns: 36px minmax(0, 1fr) 36px;
  align-items: stretch;
  border-bottom: 1px solid var(--border-subtle);
}
.record-select {
  display: grid;
  place-items: center;
  min-width: 36px;
  cursor: pointer;
}
.record-row {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr);
  align-items: start;
  gap: 0.625rem;
  width: 100%;
  min-height: 0;
  padding: 0.625rem 0.75rem;
  border: 0;
  background: transparent;
  text-align: start;
  cursor: pointer;
}
.record-row:hover,
.record-row.active {
  background: var(--surface-subtle);
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
.record-row-status {
  display: inline-flex;
  width: max-content;
  margin-top: 5px;
  padding: 2px 7px;
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
  padding: 18px 14px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: 1.45;
}
</style>
