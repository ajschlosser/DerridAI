<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { useAttrs } from "vue";
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
</script>

<template>
  <section class="review-header" :aria-label="i18n.t('pdf_corpus.review_controls')">
    <div class="review-header-status">
      <p class="review-counts">
        <span
          ><b>{{ accepted }}</b> {{ i18n.t("pdf_corpus.accepted_label") }}</span
        >
        <span
          ><b>{{ remaining }}</b> {{ i18n.t("pdf_corpus.remaining") }}</span
        >
        <span
          ><b>{{ issues }}</b> {{ i18n.t("pdf_corpus.need_attention") }}</span
        >
      </p>
      <slot name="run-status"></slot>
      <span class="review-header-spacer"></span>
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
  gap: var(--space-2) var(--space-3);
  align-items: center;
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
  padding-inline: var(--space-2);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
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
</style>
