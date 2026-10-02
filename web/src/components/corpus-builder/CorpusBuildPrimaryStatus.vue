<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, ref } from "vue";
import type { CorpusBuild } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import {
  corpusPrimaryStatus,
  corpusStageLabel,
  corpusStageRail,
} from "../../features/corpus-builder/domain/workflowPresentation";
import { isAutomatedProcessingDone } from "../../features/corpus-builder/domain/workspace";
import UiButton from "../ui/UiButton.vue";

const props = defineProps<{
  build: CorpusBuild;
  running: boolean;
  canResume: boolean;
  hasRecordTopology: boolean;
  readyCount?: number;
  enrichingCount?: number;
  preparingCount?: number;
  attentionCount?: number;
  busy?: boolean;
  providerLabel?: string;
  modelLabel?: string;
}>();
const emit = defineEmits<{
  pause: [];
  cancel: [];
  resume: [];
  delete: [];
  openReview: [];
  openPublish: [];
}>();
const i18n = useI18nStore();
const confirmingDelete = ref(false);
const status = computed(() => corpusPrimaryStatus(props.build, i18n));
const percent = computed(() => Math.round((props.build.progress || 0) * 100));
const rail = computed(() => corpusStageRail(props.build));
const operation = computed(() => status.value.detail);
const settled = computed(() => isAutomatedProcessingDone(props.build));
const recordCount = computed(() => Number(props.build.record_count || 0));
const readyCount = computed(() => Math.max(0, Number(props.readyCount || 0)));
const enrichingCount = computed(() => Math.max(0, Number(props.enrichingCount || 0)));
const preparingCount = computed(() => Math.max(0, Number(props.preparingCount || 0)));
const attentionCount = computed(() => Math.max(0, Number(props.attentionCount || 0)));
const reviewAvailableWhileRunning = computed(
  () => props.running && props.hasRecordTopology && recordCount.value > 0,
);
const reviewableCount = computed(() => readyCount.value + attentionCount.value);
const reviewLabel = computed(() =>
  reviewAvailableWhileRunning.value && readyCount.value > 0
    ? i18n.tf("pdf_corpus.primary_status.review_ready", { count: readyCount.value })
    : i18n.t("pdf_corpus.primary_status.review_records"),
);
const reviewPrimary = computed(
  () => settled.value || (reviewAvailableWhileRunning.value && reviewableCount.value > 0),
);
const showProgressiveHandoff = computed(
  () =>
    reviewAvailableWhileRunning.value &&
    ["enriching", "metadata_retry", "metadata_enrichment_rerun"].includes(
      String(props.build.stage || ""),
    ),
);
const liveCount = computed(() => {
  if (String(props.build.stage) === "enriching" && props.running) {
    return {
      label: i18n.t("pdf_corpus.primary_status.running_tasks"),
      value: Number(props.build.metadata_tasks_running || 0),
    };
  }
  return {
    label: i18n.t("pdf_corpus.need_review"),
    value: Number(props.build.needs_review_count || 0),
  };
});
const providerModel = computed(() =>
  [props.providerLabel, props.modelLabel].filter((part) => part && part !== "—").join(" · "),
);
const canDelete = computed(() => !props.running);
function confirmDelete() {
  confirmingDelete.value = false;
  emit("delete");
}
</script>

<template>
  <section
    class="corpus-build-primary-status"
    :data-tone="status.tone"
    aria-labelledby="corpus-build-status-title"
  >
    <header class="primary-status-head">
      <h2 id="corpus-build-status-title">{{ status.label }}</h2>
      <div class="primary-status-actions">
        <UiButton
          v-if="hasRecordTopology && recordCount > 0"
          :variant="reviewPrimary ? 'primary' : 'default'"
          :label="reviewLabel"
          @click="emit('openReview')"
        />
        <UiButton
          v-if="canResume"
          :label="i18n.t('pdf_corpus.resume')"
          :disabled="busy"
          @click="emit('resume')"
        />
        <UiButton v-if="running" :label="i18n.t('pdf_corpus.pause')" @click="emit('pause')" />
        <UiButton v-if="running" :label="i18n.t('pdf_corpus.cancel')" @click="emit('cancel')" />
        <UiButton
          v-if="hasRecordTopology && settled"
          :label="i18n.t('pdf_corpus.primary_status.publication_readiness')"
          @click="emit('openPublish')"
        />
        <details v-if="canDelete" class="primary-status-more">
          <summary class="btn">{{ i18n.t("pdf_corpus.more_actions") }}</summary>
          <div class="primary-status-menu" data-surface="overlay">
            <span v-if="confirmingDelete" class="delete-confirm" role="group">
              <span>{{ i18n.t("pdf_corpus.build_delete_confirm") }}</span>
              <UiButton
                variant="danger"
                :label="i18n.t('pdf_corpus.build_delete')"
                @click="confirmDelete"
              />
              <UiButton :label="i18n.t('ui.cancel')" @click="confirmingDelete = false" />
            </span>
            <UiButton
              v-else
              variant="ghost"
              :label="i18n.t('pdf_corpus.build_delete')"
              @click="confirmingDelete = true"
            />
          </div>
        </details>
      </div>
    </header>

    <p v-if="operation" class="primary-status-operation" role="status">{{ operation }}</p>
    <p v-if="reviewAvailableWhileRunning" class="primary-status-review-help">
      {{ i18n.t("pdf_corpus.primary_status.review_while_running_help") }}
    </p>

    <div class="primary-status-progress">
      <div
        class="primary-status-track"
        role="progressbar"
        :aria-label="i18n.t('pdf_corpus.build_progress')"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-valuenow="percent"
        :aria-valuetext="i18n.tf('pdf_corpus.progress_percent', { percent })"
      >
        <span :style="{ width: `${percent}%` }"></span>
      </div>
      <span class="primary-status-percent" aria-hidden="true">{{
        i18n.tf("pdf_corpus.progress_percent", { percent })
      }}</span>
    </div>

    <dl v-if="showProgressiveHandoff" class="primary-status-handoff">
      <div data-flow-state="ready">
        <dt>{{ i18n.t("pdf_corpus.primary_status.ready_for_review", "Ready for review") }}</dt>
        <dd>{{ readyCount.toLocaleString() }}</dd>
      </div>
      <div data-flow-state="enriching">
        <dt>{{ i18n.t("pdf_corpus.record_state.enriching", "Enriching") }}</dt>
        <dd>{{ enrichingCount.toLocaleString() }}</dd>
      </div>
      <div data-flow-state="preparing">
        <dt>{{ i18n.t("pdf_corpus.record_state.preparing", "Preparing") }}</dt>
        <dd>{{ preparingCount.toLocaleString() }}</dd>
      </div>
      <div data-flow-state="attention">
        <dt>{{ i18n.t("pdf_corpus.attention_required") }}</dt>
        <dd>{{ attentionCount.toLocaleString() }}</dd>
      </div>
    </dl>
    <dl class="primary-status-facts">
      <div>
        <dt>{{ i18n.t("pdf_corpus.records") }}</dt>
        <dd>{{ recordCount.toLocaleString() }}</dd>
      </div>
      <div v-if="!showProgressiveHandoff">
        <dt>{{ liveCount.label }}</dt>
        <dd>{{ liveCount.value.toLocaleString() }}</dd>
      </div>
      <div v-if="providerModel">
        <dt>{{ i18n.t("pdf_corpus.primary_status.model") }}</dt>
        <dd>{{ providerModel }}</dd>
      </div>
    </dl>

    <ol class="primary-status-rail" :aria-label="i18n.t('pdf_corpus.primary_status.stages')">
      <li
        v-for="item in rail"
        :key="item.id"
        :data-state="item.state"
        :aria-current="item.state === 'current' ? 'step' : undefined"
      >
        <span aria-hidden="true">{{
          item.state === "complete" ? "✓" : item.state === "current" ? "●" : "○"
        }}</span>
        {{ i18n.t(`pdf_corpus.rail.${item.id}`) }}
        <span class="sr-only">({{ i18n.t(`pdf_corpus.primary_status.rail_${item.state}`) }})</span>
      </li>
    </ol>
    <p class="sr-only">{{ corpusStageLabel(String(build.stage || ""), i18n) }}</p>
  </section>
</template>

<style scoped>
.primary-status-progress {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}
.primary-status-progress .primary-status-track {
  flex: 1 1 auto;
}
.primary-status-percent {
  flex: none;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  font-variant-numeric: tabular-nums;
}
.corpus-build-primary-status {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border: 1px solid var(--border-subtle);
  border-inline-start: 4px solid var(--tone-info-fg);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.corpus-build-primary-status[data-tone="success"] {
  border-inline-start-color: var(--tone-ok-fg);
}
.corpus-build-primary-status[data-tone="warning"] {
  border-inline-start-color: var(--tone-warn-fg);
}
.corpus-build-primary-status[data-tone="danger"] {
  border-inline-start-color: var(--tone-danger-fg);
}
.corpus-build-primary-status[data-tone="neutral"] {
  border-inline-start-color: var(--border-interactive);
}
.primary-status-head {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
  justify-content: space-between;
}
.primary-status-head h2 {
  margin: 0;
  font-size: var(--fs-xl);
}
.primary-status-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.primary-status-more {
  position: relative;
}
.primary-status-more > summary {
  list-style: none;
  cursor: pointer;
}
.primary-status-more > summary::-webkit-details-marker {
  display: none;
}
.primary-status-more > summary:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 2px;
}
.primary-status-menu {
  position: absolute;
  z-index: 20;
  inset-inline-end: 0;
  top: calc(100% + var(--space-1));
  min-width: 12rem;
  padding: var(--space-2);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-overlay);
  box-shadow: var(--shadow-overlay);
}
.delete-confirm {
  display: grid;
  gap: var(--space-2);
  font-size: var(--fs-sm);
}
.primary-status-operation {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.primary-status-review-help {
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border-inline-start: 3px solid var(--tone-info-border);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: var(--fs-sm);
  line-height: 1.45;
}
.primary-status-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--surface-subtle);
}
.primary-status-track span {
  display: block;
  height: 100%;
  background: var(--ui-accent);
  transition: width 0.25s;
}
.primary-status-handoff {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-2);
  margin: 0;
}
.primary-status-handoff > div {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-subtle);
}
.primary-status-handoff dt {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.primary-status-handoff dd {
  margin: 0;
  font-size: var(--fs-xl);
  font-weight: var(--fw-bold);
  font-variant-numeric: tabular-nums;
}
.primary-status-handoff [data-flow-state="ready"] {
  border-color: var(--tone-ok-border);
  background: var(--tone-ok-bg);
}
.primary-status-handoff [data-flow-state="attention"] {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
}
.primary-status-facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-6);
  margin: 0;
}
.primary-status-facts div {
  display: grid;
  gap: 2px;
}
.primary-status-facts dt {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}
.primary-status-facts dd {
  margin: 0;
  font-weight: var(--fw-bold);
}
.primary-status-rail {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.primary-status-rail li[data-state="complete"] {
  color: var(--tone-ok-fg);
}
.primary-status-rail li[data-state="current"] {
  color: var(--text-primary);
  font-weight: var(--fw-bold);
}
@media (max-width: 900px) {
  .primary-status-handoff {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 560px) {
  .primary-status-handoff {
    grid-template-columns: 1fr;
  }
}
@media (prefers-reduced-motion: reduce) {
  .primary-status-track span {
    transition: none;
  }
}
</style>
