<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import AppIcon from "../AppIcon.vue";
import PipelineGraphDiagram from "./PipelineGraphDiagram.vue";
import PipelineRunTracePanel from "./PipelineRunTracePanel.vue";
import { configurationForTrace } from "../../domain/pipelineGraph";
import {
  formatPipelineDate,
  pipelinePurposeLabel,
  pipelineRunStatusLabel,
} from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineDefinition, PipelineRunTrace, PipelineStrategy } from "../../types/pipelines";

export type PipelineRunFilters = {
  query: string;
  feature: string;
  pipelineId: string;
  status: string;
  owner: string;
};

const props = defineProps<{
  runs: PipelineRunTrace[];
  selectedRunId: string;
  pipelines: PipelineDefinition[];
  strategies?: PipelineStrategy[];
  total?: number;
  limit?: number;
  offset?: number;
  filters?: PipelineRunFilters;
  focusedRun?: PipelineRunTrace | null;
}>();

const emit = defineEmits<{
  select: [runId: string];
  apply: [filters: PipelineRunFilters];
  page: [offset: number];
  deleteRun: [runId: string];
  clearHistory: [];
  openConfiguration: [key: string];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const draft = ref<PipelineRunFilters>({
  query: "",
  feature: "",
  pipelineId: "",
  status: "",
  owner: "",
});

watch(
  () => props.filters,
  (filters) => {
    draft.value = {
      query: filters?.query || "",
      feature: filters?.feature || "",
      pipelineId: filters?.pipelineId || "",
      status: filters?.status || "",
      owner: filters?.owner || "",
    };
  },
  { immediate: true, deep: true },
);

const selectedTrace = computed(() => {
  return (
    props.runs.find((run) => run.run_id === props.selectedRunId) ||
    (props.focusedRun?.run_id === props.selectedRunId ? props.focusedRun : null) ||
    props.runs[0] ||
    null
  );
});
const configuration = computed(() =>
  selectedTrace.value ? configurationForTrace(selectedTrace.value, props.pipelines) : null,
);
const pageSize = computed(() => props.limit || props.runs.length || 25);
const total = computed(() => props.total ?? props.runs.length);
const offset = computed(() => props.offset || 0);
const pageStart = computed(() => (total.value ? offset.value + 1 : 0));
const pageEnd = computed(() => Math.min(total.value, offset.value + props.runs.length));
const features = computed(() => [...new Set(props.pipelines.map((item) => item.purpose))]);
const pipelineIds = computed(() => [...new Set(props.pipelines.map((item) => item.pipeline_id))]);
const statuses = ["completed", "failed", "cancelled", "running"];

function duration(value?: number | null) {
  if (value == null) return "—";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(value < 10000 ? 2 : 1)} s`;
}

function submitFilters() {
  emit("apply", { ...draft.value });
}

function resetFilters() {
  draft.value = { query: "", feature: "", pipelineId: "", status: "", owner: "" };
  emit("apply", { ...draft.value });
}
</script>

<template>
  <section class="trace-workspace" aria-labelledby="pipeline-runs-title">
    <header class="trace-heading">
      <div>
        <h3 id="pipeline-runs-title">{{ t("pipelines.executions_title", "Execution history") }}</h3>
        <p>
          {{
            t(
              "pipelines.executions_help",
              "Query, filter, and review every recorded run. The diagram relates what happened to the saved stage graph.",
            )
          }}
        </p>
      </div>
      <button class="btn danger" type="button" :disabled="!total" @click="emit('clearHistory')">
        {{ t("pipelines.clear_history", "Clear history") }}
      </button>
    </header>

    <form class="trace-filters" @submit.prevent="submitFilters">
      <label>
        <span>{{ t("pipelines.query", "Query") }}</span>
        <input
          v-model="draft.query"
          class="control"
          type="search"
          :placeholder="t('pipelines.query_placeholder', 'Run ID, pipeline, feature, or owner')"
        />
      </label>
      <label>
        <span>{{ t("pipelines.filter_purpose", "Purpose") }}</span>
        <select v-model="draft.feature" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="feature in features" :key="feature" :value="feature">
            {{ pipelinePurposeLabel(feature, t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.pipeline", "Pipeline") }}</span>
        <select v-model="draft.pipelineId" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="pipelineId in pipelineIds" :key="pipelineId" :value="pipelineId">
            {{ pipelineId }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.status", "Status") }}</span>
        <select v-model="draft.status" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="status in statuses" :key="status" :value="status">
            {{ pipelineRunStatusLabel(status, t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.owner", "Owner") }}</span>
        <input v-model="draft.owner" class="control" type="search" autocomplete="off" />
      </label>
      <div class="filter-actions">
        <button class="btn primary" type="submit">
          {{ t("pipelines.apply_filters", "Apply filters") }}
        </button>
        <button class="btn" type="button" @click="resetFilters">
          {{ t("pipelines.reset_filters", "Reset") }}
        </button>
      </div>
    </form>

    <p class="result-count">
      {{
        i18n.tf("pipelines.page_status", "{start}–{end} of {total}", {
          start: pageStart,
          end: pageEnd,
          total,
        })
      }}
    </p>

    <div v-if="runs.length || selectedTrace" class="trace-grid">
      <div class="run-table-wrap">
        <table class="run-table">
          <thead>
            <tr>
              <th scope="col">{{ t("pipelines.started", "Started") }}</th>
              <th scope="col">{{ t("pipelines.pipeline", "Pipeline") }}</th>
              <th scope="col">{{ t("pipelines.filter_purpose", "Purpose") }}</th>
              <th scope="col">{{ t("pipelines.status", "Status") }}</th>
              <th scope="col">{{ t("pipelines.duration", "Duration") }}</th>
              <th scope="col">
                <span class="sr-only">{{ t("pipelines.delete_run", "Delete") }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="run in runs"
              :key="run.run_id"
              :class="{ selected: selectedTrace?.run_id === run.run_id }"
              @click="emit('select', run.run_id)"
            >
              <td>
                <button type="button" class="row-select" @click.stop="emit('select', run.run_id)">
                  {{ formatPipelineDate(run.started_at, i18n.locale) }}
                </button>
              </td>
              <td>
                <strong>{{ run.pipeline_id }}</strong>
                <small>v{{ run.pipeline_version }}</small>
              </td>
              <td>{{ pipelinePurposeLabel(run.feature, t) }}</td>
              <td>{{ pipelineRunStatusLabel(run.status, t) }}</td>
              <td>{{ duration(run.total_elapsed_ms) }}</td>
              <td>
                <button
                  class="btn danger row-delete"
                  type="button"
                  :aria-label="t('pipelines.delete_run', 'Delete')"
                  @click.stop="emit('deleteRun', run.run_id)"
                >
                  <AppIcon name="trash" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="pager">
          <button
            class="btn"
            type="button"
            :disabled="offset <= 0"
            @click="emit('page', Math.max(0, offset - pageSize))"
          >
            {{ t("common.previous", "Previous") }}
          </button>
          <button
            class="btn"
            type="button"
            :disabled="offset + runs.length >= total"
            @click="emit('page', offset + pageSize)"
          >
            {{ t("common.next", "Next") }}
          </button>
        </div>
      </div>

      <div v-if="selectedTrace && configuration" class="trace-detail">
        <div class="trace-relate">
          <p>
            {{
              configuration.catalogKey
                ? t(
                    "pipelines.trace_vs_config",
                    "The diagram overlays what ran on the saved stage graph. Stages that did not run stay visible.",
                  )
                : t(
                    "pipelines.configuration_missing",
                    "This version is not in the current catalog. The diagram uses the configuration stored with the trace.",
                  )
            }}
          </p>
          <button
            v-if="configuration.catalogKey"
            class="btn"
            type="button"
            @click="emit('openConfiguration', configuration.catalogKey)"
          >
            {{ t("pipelines.open_configuration", "Open configuration") }}
          </button>
        </div>
        <PipelineGraphDiagram
          :stages="configuration.stages"
          :entry-stage-ids="configuration.entryStageIds"
          :strategies="strategies || []"
          :execution="selectedTrace"
          :title="t('pipelines.execution_diagram', 'Execution diagram')"
          :description="
            t(
              'pipelines.execution_diagram_help',
              'Filled nodes ran. Dim nodes are configured steps this run did not reach. A dashed outline is a step observed only in the trace.',
            )
          "
        />
        <details class="trace-audit">
          <summary>{{ t("pipelines.stage_details", "Stage details") }}</summary>
          <PipelineRunTracePanel :trace="selectedTrace" />
        </details>
      </div>
    </div>

    <div v-else class="empty-state">
      <AppIcon name="history" />
      <div>
        <strong>{{ t("pipelines.no_matching_runs", "No executions match these filters.") }}</strong>
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
  gap: 14px;
}
.trace-heading,
.trace-relate,
.filter-actions,
.pager {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.trace-heading h3 {
  margin: 0;
  font-size: 1rem;
}
.trace-heading p,
.trace-relate p,
.result-count {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.5;
}
.trace-filters {
  display: grid;
  grid-template-columns: minmax(180px, 1.4fr) repeat(4, minmax(120px, 1fr));
  gap: 10px;
  align-items: end;
}
.trace-filters label {
  display: grid;
  gap: 4px;
  font-size: 0.75rem;
}
.trace-filters .control {
  width: 100%;
  min-height: 36px;
}
.filter-actions {
  grid-column: 1 / -1;
  justify-content: flex-start;
}
.run-table-wrap,
.trace-detail {
  display: grid;
  gap: 12px;
  min-width: 0;
}
.run-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}
.run-table th,
.run-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: middle;
}
.run-table th {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 650;
}
.run-table tr.selected {
  background: var(--soft);
}
.run-table small {
  display: block;
  color: var(--muted);
}
.row-select {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.row-select:focus-visible,
.row-delete:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}
.row-delete {
  min-width: 36px;
  min-height: 36px;
  padding: 6px;
}
.row-delete :deep(svg) {
  width: 14px;
  height: 14px;
}
.trace-detail {
  padding-top: 4px;
}
.trace-audit {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.trace-audit summary {
  padding: 10px 12px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 750;
}
.trace-audit summary:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: -2px;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.empty-state {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  color: var(--muted);
}
.empty-state strong {
  color: inherit;
}
.empty-state p {
  margin: 4px 0 0;
}
@media (max-width: 1100px) {
  .trace-filters {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
