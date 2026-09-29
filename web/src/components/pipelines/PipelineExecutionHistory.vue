<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import PipelineRunTracePanel from "./PipelineRunTracePanel.vue";
import { formatPipelineDate, pipelineRunStatusLabel } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineRunTrace } from "../../types/pipelines";

const props = defineProps<{
  runs: PipelineRunTrace[];
  selectedRunId: string;
}>();

const emit = defineEmits<{
  select: [runId: string];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const selectedTrace = computed(
  () => props.runs.find((run) => run.run_id === props.selectedRunId) || props.runs[0] || null,
);
</script>

<template>
  <section class="trace-workspace" aria-labelledby="pipeline-runs-title">
    <header>
      <h3 id="pipeline-runs-title">{{ t("pipelines.recent_runs", "Recent executions") }}</h3>
      <p>
        {{
          t(
            "pipelines.recent_runs_help",
            "Trace the strategy path, fallbacks, candidate counts, models, collections, and timings that actually ran.",
          )
        }}
      </p>
    </header>

    <div v-if="runs.length" class="trace-grid">
      <div
        class="run-list"
        role="list"
        :aria-label="t('pipelines.recent_runs', 'Recent executions')"
      >
        <button
          v-for="run in runs"
          :key="run.run_id"
          type="button"
          :class="{ selected: selectedTrace?.run_id === run.run_id }"
          :aria-current="selectedTrace?.run_id === run.run_id ? 'true' : undefined"
          @click="emit('select', run.run_id)"
        >
          <span>
            <strong>{{ run.pipeline_id }} v{{ run.pipeline_version }}</strong>
            <small>{{ run.feature }}</small>
          </span>
          <span>
            <strong>{{ pipelineRunStatusLabel(run.status, t) }}</strong>
            <small>{{ formatPipelineDate(run.started_at, i18n.locale) }}</small>
          </span>
        </button>
      </div>
      <PipelineRunTracePanel v-if="selectedTrace" :trace="selectedTrace" />
    </div>

    <div v-else class="empty-state">
      <AppIcon name="history" />
      <div>
        <strong>{{ t("pipelines.no_runs", "No pipeline traces yet") }}</strong>
        <p>
          {{
            t("pipelines.no_runs_help", "New Research runs will appear here once they complete.")
          }}
        </p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.trace-workspace {
  display: grid;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.trace-workspace > header h3 {
  margin: 0;
  font-size: 1rem;
}
.trace-workspace > header p {
  max-width: 780px;
  margin: 5px 0 0;
  color: var(--muted);
  line-height: 1.5;
}
.trace-grid {
  display: grid;
  grid-template-columns: minmax(220px, 0.35fr) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.run-list {
  display: grid;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 12px;
}
.run-list button {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  min-height: 44px;
  padding: 10px 11px;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.run-list button:last-child {
  border-bottom: 0;
}
.run-list button:hover,
.run-list button.selected {
  background: var(--soft);
}
.run-list button:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: -2px;
}
.run-list button span {
  display: grid;
  gap: 2px;
}
.run-list button span:last-child {
  justify-items: end;
  text-align: right;
}
.run-list strong,
.run-list small {
  font-size: 0.75rem;
}
.run-list small {
  color: var(--muted);
}
.empty-state {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--soft);
}
.empty-state :deep(svg) {
  width: 15px;
  height: 15px;
}
.empty-state p {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 0.78rem;
}
@media (max-width: 960px) {
  .trace-grid {
    grid-template-columns: 1fr;
  }
}
</style>
