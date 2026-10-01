<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { onBeforeUnmount, onMounted, ref } from "vue";
import type { ReviewWorkspaceMode } from "../../features/corpus-builder/composables/useCorpusReviewWorkspace";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";

export type ReviewInspectorTab = "metadata" | "evidence" | "source" | "semantic";

/**
 * The inspector frame for Review: the detail-workspace heading for the full-width Metadata and Source
 * layouts, and the Metadata / Evidence / Source / Map tab bar for the split view. The active panel is
 * the default slot, chosen by the parent, which owns every mutation.
 */
const props = defineProps<{
  mode: ReviewWorkspaceMode;
  hasRecord: boolean;
  blockerCount: number;
}>();
const emit = defineEmits<{
  backToRecord: [];
  tabKeydown: [event: KeyboardEvent];
  rootChange: [element: HTMLElement | null];
}>();
const tab = defineModel<ReviewInspectorTab>("tab", { required: true });
const i18n = useI18nStore();
const root = ref<HTMLElement | null>(null);
onMounted(() => emit("rootChange", root.value));
onBeforeUnmount(() => emit("rootChange", null));
const tabs: Array<{ id: ReviewInspectorTab; key: string }> = [
  { id: "metadata", key: "pdf_corpus.metadata_tab" },
  { id: "evidence", key: "pdf_corpus.evidence_tab" },
  { id: "source", key: "pdf_corpus.source_tab" },
  { id: "semantic", key: "pdf_corpus.semantic_tab" },
];
</script>

<template>
  <aside ref="root" class="review-inspector" :aria-label="i18n.t('pdf_corpus.review_details')">
    <div v-if="props.mode !== 'record'" class="detail-workspace-head">
      <div>
        <span class="eyebrow">{{ i18n.t("pdf_corpus.review_workspace") }}</span>
        <h3>
          {{
            props.mode === "metadata"
              ? i18n.t("pdf_corpus.workspace.metadata")
              : i18n.t("pdf_corpus.workspace.source")
          }}
        </h3>
        <p>
          {{
            props.mode === "metadata"
              ? i18n.t("pdf_corpus.workspace.metadata_help")
              : i18n.t("pdf_corpus.workspace.source_help")
          }}
        </p>
      </div>
      <UiButton
        size="small"
        :label="i18n.t('pdf_corpus.workspace.back_record')"
        @click="emit('backToRecord')"
      />
    </div>
    <div
      v-if="props.mode === 'record' && props.hasRecord"
      class="review-inspector-tabs"
      role="tablist"
      :aria-label="i18n.t('pdf_corpus.review_detail_views')"
    >
      <button
        v-for="item in tabs"
        :id="`review-tab-${item.id}`"
        :key="item.id"
        :data-review-tab="item.id"
        type="button"
        role="tab"
        :aria-controls="`review-panel-${item.id}`"
        :aria-selected="tab === item.id"
        :tabindex="tab === item.id ? 0 : -1"
        @keydown="emit('tabKeydown', $event)"
        @click="tab = item.id"
      >
        {{ i18n.t(item.key)
        }}<span v-if="item.id === 'metadata' && props.blockerCount">{{ props.blockerCount }}</span>
      </button>
    </div>
    <slot></slot>
  </aside>
</template>

<style scoped>
.review-inspector {
  min-width: 0;
  overflow-x: hidden;
  border-inline-start: 1px solid var(--border-subtle);
  background: var(--surface-card);
}
.eyebrow {
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--text-secondary);
  font-weight: 700;
}
.review-inspector-tabs {
  position: sticky;
  top: 0;
  z-index: 6;
  display: grid;
  /* One row however many tabs there are (the semantic map is a fourth). */
  grid-auto-flow: column;
  grid-auto-columns: minmax(max-content, 1fr);
  overflow-x: auto;
  scrollbar-width: none;
  background: var(--surface-card);
  border-bottom: 1px solid var(--border-subtle);
}
.review-inspector-tabs button {
  min-height: 44px;
  min-width: 0;
  padding-inline: 4px;
  white-space: nowrap;
  border: 0;
  border-inline-end: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 800;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
}
.review-inspector-tabs button[aria-selected="true"] {
  background: var(--surface-subtle);
  color: var(--text-primary);
  box-shadow: inset 0 -3px 0 var(--ui-accent);
}
.review-inspector-tabs button:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: -3px;
}
.review-inspector-tabs button span {
  min-width: 18px;
  border-radius: 999px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  padding: 1px 5px;
  font-size: 0.8125rem;
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
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-card);
}
.detail-workspace-head h3 {
  margin: 2px 0 4px;
  font-size: 1.05rem;
}
.detail-workspace-head p {
  margin: 0;
  max-width: 78ch;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: 1.5;
}
/* In the full-width layouts the tab bar would sit under the heading, so it follows it. */
.detail-workspace-head ~ .review-inspector-tabs {
  top: 94px;
}
@media (max-width: 1050px) {
  .detail-workspace-head {
    position: static;
  }
  .detail-workspace-head ~ .review-inspector-tabs {
    top: 0;
  }
}
@media (max-width: 760px) {
  .review-inspector-tabs {
    top: 0;
  }
}
</style>
