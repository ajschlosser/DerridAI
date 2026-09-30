<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import type { MetadataSchema } from "../../api/metadataSchemas";
import type { ReviewQueue } from "../../types/corpus";
import { useI18nStore } from "../../stores/i18n";
import CorpusActionMenu, { type CorpusActionMenuItem } from "../CorpusActionMenu.vue";
import CorpusBulkMetadataEditor from "../CorpusBulkMetadataEditor.vue";
import CorpusReviewQueueTabs from "../CorpusReviewQueueTabs.vue";
import UiButton from "../ui/UiButton.vue";
import UiDialog from "../ui/UiDialog.vue";

const props = defineProps<{
  total: number;
  ready: number;
  issues: number;
  metadata: number;
  topology: number;
  sourceProblems: number;
  accepted: number;
  rejected: number;
  bulkActionItems: CorpusActionMenuItem[];
  bulkActionFeedback: string;
  bulkMetadataOpen: boolean;
  schema?: MetadataSchema | null;
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
const confirmingAcceptClean = ref(false);
const selectedEdit = computed(() => props.bulkActionItems.find((item) => item.id === "edit"));
const selectedReject = computed(() => props.bulkActionItems.find((item) => item.id === "reject"));
const menuItems = computed(() =>
  props.bulkActionItems.filter(
    (item) => item.id !== "reject" && !(props.selectedCount > 0 && item.id === "edit"),
  ),
);

function confirmAcceptClean() {
  confirmingAcceptClean.value = false;
  emit("acceptClean");
}
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

    <div class="review-bulk">
      <UiButton
        v-if="props.ready > 0"
        size="small"
        variant="primary"
        button-class="review-ready-action"
        :disabled="props.disabled"
        @click="confirmingAcceptClean = true"
      >
        {{ i18n.tf("pdf_corpus.accept_clean", { count: props.ready }) }}
      </UiButton>
      <CorpusActionMenu
        v-if="menuItems.length"
        :label="
          props.selectedCount > 0
            ? i18n.t('pdf_corpus.more_actions')
            : i18n.t('pdf_corpus.bulk_actions')
        "
        :items="menuItems"
        :disabled="props.disabled"
        placement="bottom"
        @select="emit('bulkAction', $event)"
      />
    </div>

    <div
      v-if="props.selectedCount > 0"
      class="review-selection-bar"
      role="group"
      :aria-label="i18n.t('pdf_corpus.bulk_selected_records')"
    >
      <strong>{{
        i18n.tf("pdf_corpus.bulk_selected_count", { count: props.selectedCount })
      }}</strong>
      <span class="review-selection-spacer"></span>
      <UiButton
        v-if="selectedEdit"
        size="small"
        :label="selectedEdit.label"
        :disabled="Boolean(selectedEdit.reason) || props.disabled"
        :disabled-reason="selectedEdit.reason"
        @click="emit('bulkAction', 'edit')"
      />
      <UiButton
        v-if="selectedReject"
        size="small"
        variant="danger"
        :label="selectedReject.label"
        :disabled="Boolean(selectedReject.reason) || props.disabled"
        :disabled-reason="selectedReject.reason"
        @click="emit('bulkAction', 'reject')"
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
      <UiButton size="small" :disabled="!props.hasPreviousPage" @click="emit('previousPage')">
        {{ i18n.t("ui.previous") }}
      </UiButton>
      <span>{{ props.pageNumber }} / {{ props.pageCount }}</span>
      <UiButton size="small" :disabled="!props.hasNextPage" @click="emit('nextPage')">
        {{ i18n.t("ui.next") }}
      </UiButton>
    </div>

    <UiDialog
      :open="confirmingAcceptClean"
      size="medium"
      :title="i18n.tf('pdf_corpus.accept_clean', { count: props.ready })"
      :description="i18n.tf('pdf_corpus.accept_clean_confirm', { count: props.ready })"
      :close-label="i18n.t('ui.close')"
      @close="confirmingAcceptClean = false"
    >
      <p class="accept-ready-dialog-copy">
        {{ i18n.t("pdf_corpus.accept_clean_authority_help") }}
      </p>
      <template #footer>
        <UiButton :label="i18n.t('ui.cancel')" @click="confirmingAcceptClean = false" />
        <UiButton
          variant="primary"
          :label="i18n.tf('pdf_corpus.accept_clean', { count: props.ready })"
          :disabled="props.disabled"
          @click="confirmAcceptClean"
        />
      </template>
    </UiDialog>
  </section>
</template>

<style scoped>
/* The lower half of the consolidated review header. The header owns the surface and stickiness. */
.review-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-3);
  align-items: center;
  font-size: var(--fs-sm);
}
.review-toolbar > :first-child {
  flex: 0 1 auto;
}
.review-toolbar .control {
  min-height: 40px;
  flex: 1 1 14rem;
  max-width: 24rem;
  font-size: var(--fs-sm);
}
.review-bulk {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.review-ready-action {
  font-weight: var(--fw-bold);
}
.review-selection-bar {
  flex: 1 1 100%;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-interactive);
  border-radius: var(--radius-control);
  background: var(--surface-selected);
  font-size: var(--fs-sm);
}
.review-selection-bar strong {
  color: var(--text-primary);
}
.review-selection-spacer {
  flex: 1 1 0;
}
.review-action-feedback {
  flex: 1 1 100%;
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--tone-ok-border);
  border-radius: var(--radius-control);
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
  font-size: var(--fs-sm);
  line-height: 1.5;
}
.accept-ready-dialog-copy {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.5;
}
.pager {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  margin-inline-start: auto;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.review-toolbar > :is(section, form, aside) {
  flex: 1 1 100%;
}
</style>
