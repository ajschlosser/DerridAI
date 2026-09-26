<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import type { CorpusRecord } from "../../api/corpus";
import type { MetadataSchema } from "../../api/metadataSchemas";
import type { ReviewQueue } from "../../types/corpus";
import type { ReviewWorkspaceMode } from "../../features/corpus-builder/composables/useCorpusReviewWorkspace";
import { useI18nStore } from "../../stores/i18n";
import CorpusActionMenu, { type CorpusActionMenuItem } from "../CorpusActionMenu.vue";
import CorpusBulkMetadataEditor from "../CorpusBulkMetadataEditor.vue";
import CorpusReviewQueueTabs from "../CorpusReviewQueueTabs.vue";

const props = defineProps<{
  total: number;
  ready: number;
  issues: number;
  metadata: number;
  topology: number;
  sourceProblems: number;
  accepted: number;
  rejected: number;
  workspaceMode: ReviewWorkspaceMode;
  hasSelectedRecord: boolean;
  bulkActionItems: CorpusActionMenuItem[];
  bulkActionFeedback: string;
  bulkMetadataOpen: boolean;
  schema?: MetadataSchema | null;
  records: CorpusRecord[];
  knownValues: Record<string, string[]>;
  regionTypes: string[];
  discourseRoles: string[];
  selectedCount: number;
  bulkTotalCount: number;
  bulkDisabled: boolean;
  pageNumber: number;
  pageCount: number;
  hasPreviousPage: boolean;
  hasNextPage: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  workspace: [mode: ReviewWorkspaceMode];
  acceptClean: [];
  bulkAction: [id: string];
  bulkApply: [payload: { changes: Record<string, unknown>; applyToAll: boolean }];
  bulkClose: [];
  previousPage: [];
  nextPage: [];
}>();

const queue = defineModel<ReviewQueue>("queue", { required: true });
const query = defineModel<string>("query", { required: true });
const i18n = useI18nStore();
</script>

<template>
  <section class="review-toolbar" :aria-label="i18n.t('pdf_corpus.review_controls')">
    <CorpusReviewQueueTabs
      v-model="queue"
      :total="props.total"
      :ready="props.ready"
      :issues="props.issues"
      :metadata="props.metadata"
      :topology="props.topology"
      :source-problems="props.sourceProblems"
      :accepted="props.accepted"
      :rejected="props.rejected"
      :disabled="props.disabled"
    />

    <label class="sr-only" for="pdf-corpus-record-search">
      {{ i18n.t("pdf_corpus.search_records") }}
    </label>
    <input
      id="pdf-corpus-record-search"
      v-model="query"
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
        :aria-pressed="props.workspaceMode === 'record'"
        @click="emit('workspace', 'record')"
      >
        {{ i18n.t("pdf_corpus.workspace.record") }}
      </button>
      <button
        type="button"
        class="btn small"
        :aria-pressed="props.workspaceMode === 'metadata'"
        :aria-label="i18n.t('pdf_corpus.workspace.metadata')"
        :disabled="!props.hasSelectedRecord"
        @click="emit('workspace', 'metadata')"
      >
        {{ i18n.t("pdf_corpus.workspace.metadata_short") }}
      </button>
      <button
        type="button"
        class="btn small"
        :aria-pressed="props.workspaceMode === 'source'"
        :aria-label="i18n.t('pdf_corpus.workspace.source')"
        :disabled="!props.hasSelectedRecord"
        @click="emit('workspace', 'source')"
      >
        {{ i18n.t("pdf_corpus.workspace.source_short") }}
      </button>
    </div>

    <div class="review-bulk">
      <button
        type="button"
        class="btn small primary"
        :disabled="props.disabled || props.ready === 0"
        @click="emit('acceptClean')"
      >
        {{ i18n.tf("pdf_corpus.accept_clean", { count: props.ready }) }}
      </button>
      <CorpusActionMenu
        :label="i18n.t('pdf_corpus.bulk_actions')"
        :items="props.bulkActionItems"
        :disabled="props.disabled"
        placement="bottom"
        @select="emit('bulkAction', $event)"
      />
    </div>

    <p
      v-if="props.bulkActionFeedback"
      class="review-action-feedback"
      role="status"
      aria-live="polite"
    >
      {{ props.bulkActionFeedback }}
    </p>

    <CorpusBulkMetadataEditor
      v-if="props.bulkMetadataOpen"
      :schema="props.schema"
      :records="props.records"
      :known-values="props.knownValues"
      :region-types="props.regionTypes"
      :discourse-roles="props.discourseRoles"
      :selected-count="props.selectedCount"
      :total-count="props.bulkTotalCount"
      :disabled="props.bulkDisabled"
      @apply="emit('bulkApply', $event)"
      @close="emit('bulkClose')"
    />

    <div class="pager">
      <button
        type="button"
        class="btn small"
        :disabled="!props.hasPreviousPage"
        @click="emit('previousPage')"
      >
        {{ i18n.t("ui.previous") }}
      </button>
      <span>{{ props.pageNumber }} / {{ props.pageCount }}</span>
      <button
        type="button"
        class="btn small"
        :disabled="!props.hasNextPage"
        @click="emit('nextPage')"
      >
        {{ i18n.t("ui.next") }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.review-toolbar {
  position: sticky;
  top: 66px;
  z-index: 11;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 320px) auto;
  gap: 0.5rem 0.75rem;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: color-mix(in srgb, var(--surface-card) 96%, transparent);
  backdrop-filter: blur(12px);
  font-size: 0.8125rem;
}
.review-toolbar .control {
  min-height: 40px;
  font-size: 0.8125rem;
}
.workspace-switcher {
  display: inline-flex;
  gap: 2px;
  align-items: center;
  flex-wrap: nowrap;
  padding: 2px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}
.workspace-switcher .btn {
  border-color: transparent;
  background: transparent;
  box-shadow: none;
}
.workspace-switcher .btn[aria-pressed="true"] {
  border-color: var(--border-subtle);
  background: var(--surface-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-card);
}
.review-bulk {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.review-bulk .btn {
  min-height: 34px;
}
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
}
.pager {
  grid-column: 1/-1;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--muted);
}

@media (min-width: 1280px) {
  .review-toolbar {
    grid-template-columns: minmax(10rem, 1fr) auto auto;
  }
  .review-toolbar > :first-child {
    grid-column: 1/3;
  }
  .pager {
    grid-column: 3;
    grid-row: 1;
    justify-self: end;
  }
  #pdf-corpus-record-search {
    grid-column: 1;
  }
  .workspace-switcher {
    grid-column: 2;
  }
  .review-bulk {
    grid-column: 3;
    flex-wrap: nowrap;
  }
  .review-action-feedback {
    grid-column: 1/-1;
  }
  .review-toolbar > :is(section, form, aside) {
    grid-column: 1/-1;
  }
}

@media (max-width: 1279.98px) {
  .review-toolbar {
    display: flex;
    flex-wrap: wrap;
  }
  .review-toolbar > :first-child {
    flex: 1 1 100%;
  }
  .pager {
    order: 9;
    margin-inline-start: auto;
  }
  #pdf-corpus-record-search {
    flex: 1 1 12rem;
  }
  .review-bulk {
    flex-wrap: wrap;
  }
  .review-action-feedback,
  .review-toolbar > :is(section, form, aside) {
    flex: 1 1 100%;
  }
}
</style>
