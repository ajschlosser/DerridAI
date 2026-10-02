<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, useAttrs } from "vue";
import type { ReviewQueue } from "../../types/corpus";
import type { ReviewWorkspaceMode } from "../../features/corpus-builder/composables/useCorpusReviewWorkspace";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import CorpusReviewToolbar from "./CorpusReviewToolbar.vue";

/**
 * One contiguous surface for everything above the review panes: progress, background run status,
 * the Record/Metadata/Source view, queue filters, search, bulk actions and paging. Props this header
 * does not declare (bulk editor, paging, counts) fall through to the toolbar below.
 */
defineOptions({ inheritAttrs: false });
defineProps<{
  accepted: number;
  ready: number;
  issues: number;
  remaining: number;
  /** All Records in the build, the denominator of the progress meter. */
  reviewTotal: number;
  workspaceMode: ReviewWorkspaceMode;
  hasSelectedRecord: boolean;
  focusDisabled?: boolean;
}>();
const emit = defineEmits<{ focus: []; workspace: [mode: ReviewWorkspaceMode] }>();
const queue = defineModel<ReviewQueue>("queue", { required: true });
const query = defineModel<string>("query", { required: true });
const i18n = useI18nStore();
type ToolbarProps = InstanceType<typeof CorpusReviewToolbar>["$props"];
const attrs = useAttrs();
/** Everything the header does not declare belongs to the toolbar (counts, bulk editor, paging). */
// A function, not a computed: attrs are not reactive, but every change re-renders this component.
const toolbarProps = () => ({ ...attrs }) as unknown as ToolbarProps;
const views: Array<{ id: ReviewWorkspaceMode; key: string }> = [
  { id: "record", key: "pdf_corpus.workspace.record" },
  { id: "metadata", key: "pdf_corpus.workspace.metadata_short" },
  { id: "source", key: "pdf_corpus.workspace.source_short" },
];
const viewLabels: Record<ReviewWorkspaceMode, string> = {
  record: "pdf_corpus.workspace.record",
  metadata: "pdf_corpus.workspace.metadata",
  source: "pdf_corpus.workspace.source",
};
const issueQueueActive = computed(() =>
  ["issues", "metadata", "topology", "source"].includes(queue.value),
);
</script>

<template>
  <section class="review-header" :aria-label="i18n.t('pdf_corpus.review_controls')">
    <div class="review-header-status">
      <div class="review-progress" role="group" :aria-label="i18n.t('pdf_corpus.review_progress')">
        <p class="review-counts">
          <span
            ><b>{{
              i18n.tf("pdf_corpus.review_progress_summary", { accepted, total: reviewTotal })
            }}</b></span
          >
          <span
            ><b>{{ remaining }}</b> {{ i18n.t("pdf_corpus.remaining") }}</span
          >
        </p>
        <progress
          class="review-meter"
          :max="Math.max(reviewTotal, 1)"
          :value="accepted"
          :aria-label="i18n.t('pdf_corpus.review_progress')"
        ></progress>
      </div>

      <div
        class="review-status-shortcuts"
        role="group"
        :aria-label="i18n.t('pdf_corpus.review_queue')"
      >
        <button
          type="button"
          data-queue-shortcut="issues"
          :aria-pressed="issueQueueActive"
          @click="queue = 'issues'"
        >
          <span>{{ i18n.t("pdf_corpus.queue_tab.issues", "Needs attention") }}</span>
          <b>{{ issues.toLocaleString() }}</b>
        </button>
        <button
          type="button"
          data-queue-shortcut="ready"
          :aria-pressed="queue === 'ready'"
          @click="queue = 'ready'"
        >
          <span>{{ i18n.t("pdf_corpus.queue_tab.ready", "Ready") }}</span>
          <b>{{ ready.toLocaleString() }}</b>
        </button>
        <button
          type="button"
          data-queue-shortcut="accepted"
          :aria-pressed="queue === 'accepted'"
          @click="queue = 'accepted'"
        >
          <span>{{ i18n.t("pdf_corpus.queue_accepted", "Accepted") }}</span>
          <b>{{ accepted.toLocaleString() }}</b>
        </button>
      </div>

      <slot name="run-status"></slot>
      <span class="review-header-spacer"></span>
      <div class="review-header-actions">
        <UiButton
          size="small"
          :label="i18n.t('pdf_corpus.focus_view')"
          :disabled="focusDisabled"
          @click="emit('focus')"
        />
        <div class="review-view" role="group" :aria-label="i18n.t('pdf_corpus.review_view')">
          <span class="review-view-label">{{ i18n.t("pdf_corpus.review_view") }}</span>
          <button
            v-for="view in views"
            :key="view.id"
            type="button"
            class="review-view-option"
            :aria-pressed="workspaceMode === view.id"
            :aria-label="i18n.t(viewLabels[view.id])"
            :disabled="view.id !== 'record' && !hasSelectedRecord"
            @click="emit('workspace', view.id)"
          >
            {{ i18n.t(view.key) }}
          </button>
        </div>
      </div>
    </div>
    <CorpusReviewToolbar
      v-bind="toolbarProps()"
      v-model:queue="queue"
      v-model:query="query"
      :accepted="accepted"
      :ready="ready"
      :issues="issues"
    />
  </section>
</template>

<style scoped>
.review-header {
  container-type: inline-size;
  display: grid;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  font-size: var(--fs-sm);
}
.review-header-status {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  align-items: center;
}
.review-status-shortcuts {
  display: inline-grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(6.75rem, 1fr);
  gap: 2px;
  padding: 2px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}
.review-status-shortcuts button {
  min-height: 40px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-2);
  align-items: center;
  padding: 0.35rem 0.65rem;
  border: 1px solid transparent;
  border-radius: calc(var(--radius-control) - 2px);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font: inherit;
  font-size: var(--fs-xs);
  text-align: start;
}
.review-status-shortcuts button b {
  color: var(--text-primary);
  font-size: var(--fs-sm);
}
.review-status-shortcuts button[aria-pressed="true"] {
  border-color: var(--border-subtle);
  background: var(--surface-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}
.review-status-shortcuts button[data-queue-shortcut="issues"] b {
  color: var(--tone-warn-fg);
}
.review-status-shortcuts button:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
.review-header-actions {
  display: inline-flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
  justify-content: flex-end;
}
.review-counts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  margin: 0;
  color: var(--text-secondary);
}
.review-counts b {
  color: var(--text-primary);
}
.review-progress {
  display: grid;
  gap: 3px;
  min-width: 10rem;
}
.review-meter {
  inline-size: 100%;
  block-size: 6px;
  appearance: none;
  border: 0;
  border-radius: 999px;
  background: var(--surface-subtle);
  overflow: hidden;
}
.review-meter::-webkit-progress-bar {
  background: var(--border-subtle);
}
.review-meter::-webkit-progress-value {
  background: var(--ui-accent);
}
.review-meter::-moz-progress-bar {
  background: var(--ui-accent);
}
.review-header-spacer {
  flex: 1 1 0;
}
.review-view {
  display: inline-flex;
  gap: 2px;
  align-items: center;
  padding: 2px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}
.review-view-label {
  padding-inline: var(--space-2) var(--space-1);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.review-view-option {
  min-height: 30px;
  padding: 0 var(--space-3);
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font: inherit;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.review-view-option[aria-pressed="true"] {
  border-color: var(--border-subtle);
  background: var(--surface-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}
.review-view-option:disabled {
  cursor: not-allowed;
  font-weight: normal;
}
.review-view-option:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
@container (max-width: 54rem) {
  .review-status-shortcuts {
    order: 3;
    inline-size: 100%;
    grid-auto-columns: minmax(0, 1fr);
  }
  .review-header-spacer {
    display: none;
  }
  .review-header-actions {
    margin-inline-start: auto;
  }
}
@container (max-width: 42rem) {
  .review-header-actions {
    inline-size: 100%;
    justify-content: space-between;
  }
  .review-view-label {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
  }
  .review-status-shortcuts button {
    grid-template-columns: 1fr;
    gap: 1px;
    text-align: center;
  }
}
</style>
