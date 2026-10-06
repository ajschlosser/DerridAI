<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import PipelineExecutionFilters from "./PipelineExecutionFilters.vue";
import PipelineExecutionInspector from "./PipelineExecutionInspector.vue";
import PipelineExecutionList from "./PipelineExecutionList.vue";
import UiButton from "../ui/UiButton.vue";
import UiMenu, { type UiMenuItem } from "../ui/UiMenu.vue";
import type { PipelineRunFilters } from "../../features/pipelines/composables/usePipelineStudioNavigation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelinePurpose,
  PipelineRunTrace,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

export type { PipelineRunFilters };

const props = defineProps<{
  runs: PipelineRunTrace[];
  pipelines: PipelineDefinition[];
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  strategies: PipelineStrategy[];
  selectedRunId: string;
  focusedRun: PipelineRunTrace | null;
  total: number;
  limit: number;
  offset: number;
  filters: PipelineRunFilters;
  pending: boolean;
  refreshing: boolean;
  error: string;
}>();
const emit = defineEmits<{
  select: [runId: string];
  apply: [filters: PipelineRunFilters];
  page: [offset: number];
  deleteRun: [runId: string];
  clearHistory: [];
  openConfiguration: [key: string];
  retry: [];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const selectedRun = computed(
  () =>
    props.runs.find((run) => run.run_id === props.selectedRunId) ||
    (props.focusedRun?.run_id === props.selectedRunId ? props.focusedRun : null) ||
    props.runs[0] ||
    null,
);
const pageStart = computed(() => (props.total ? props.offset + 1 : 0));
const pageEnd = computed(() => Math.min(props.total, props.offset + props.runs.length));
const resultLabel = computed(() =>
  i18n.tf("pipelines.page_status", "{start}–{end} of {total}", {
    start: pageStart.value,
    end: pageEnd.value,
    total: props.total,
  }),
);
const menuItems = computed<UiMenuItem[]>(() => [
  {
    id: "clear",
    label: t("pipelines.clear_history_menu", "Clear execution history"),
    reason: props.total
      ? undefined
      : t("pipelines.clear_history_empty", "There are no executions to clear."),
  },
]);
</script>

<template>
  <section
    id="pipeline-panel-executions"
    class="executions-workspace"
    role="tabpanel"
    aria-labelledby="pipeline-tab-executions"
  >
    <header class="workspace-heading">
      <h2 id="pipeline-runs-title">{{ t("pipelines.executions_title", "Execution history") }}</h2>
      <p>
        {{
          t(
            "pipelines.executions_help",
            "Query, filter, and review every recorded run. The diagram relates what happened to the saved stage graph.",
          )
        }}
      </p>
    </header>

    <PipelineExecutionFilters
      :filters="filters"
      :pipelines="pipelines"
      :purposes="purposes"
      :vocabulary="vocabulary"
      :result-label="resultLabel"
      @apply="emit('apply', $event)"
    >
      <template #menu>
        <UiMenu
          :label="t('pipelines.more_actions', 'More')"
          :items="menuItems"
          align="end"
          @select="emit('clearHistory')"
        />
      </template>
    </PipelineExecutionFilters>

    <div v-if="pending" class="workspace-state" role="status">
      {{ t("pipelines.executions_loading", "Loading execution history…") }}
    </div>

    <div v-else-if="error && !runs.length && !selectedRun" class="workspace-state error" role="alert">
      <div>
        <strong>{{ t("pipelines.executions_failed", "Could not load execution history.") }}</strong>
        <p>{{ error }}</p>
      </div>
      <UiButton :label="t('common.retry', 'Retry')" @click="emit('retry')" />
    </div>

    <div v-else>
      <div v-if="refreshing" class="workspace-state inline" role="status">
        {{ t("loading.updating", "Updating…") }}
      </div>
      <div v-if="error && (runs.length || selectedRun)" class="workspace-state error inline" role="alert">
        <div>
          <strong>{{ t("loading.stale", "Showing previously loaded data.") }}</strong>
          <p>{{ error }}</p>
        </div>
        <UiButton :label="t('common.retry', 'Retry')" @click="emit('retry')" />
      </div>

      <div v-if="runs.length || selectedRun" class="pipeline-execution-layout">
      <PipelineExecutionList
        :runs="runs"
        :pipelines="pipelines"
        :purposes="purposes"
        :vocabulary="vocabulary"
        :selected-run-id="selectedRun?.run_id || ''"
        :total="total"
        :limit="limit || runs.length || 25"
        :offset="offset"
        @select="emit('select', $event)"
        @page="emit('page', $event)"
        @delete-run="emit('deleteRun', $event)"
        @open-configuration="emit('openConfiguration', $event)"
      />
      <div v-if="selectedRun" class="pipeline-execution-inspector-scroll">
        <PipelineExecutionInspector
          :run="selectedRun"
          :pipelines="pipelines"
          :purposes="purposes"
          :vocabulary="vocabulary"
          :strategies="strategies"
          @open-configuration="emit('openConfiguration', $event)"
        />
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
    </div>
  </section>
</template>

<style scoped>
.executions-workspace {
  display: grid;
  gap: var(--space-3);
}
.workspace-heading h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.125rem;
}
.workspace-heading p {
  max-width: var(--measure);
  margin: var(--space-1) 0 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.workspace-state {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  min-height: 72px;
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  color: var(--text-secondary);
}
.workspace-state.inline {
  min-height: 0;
  padding-block: var(--space-2);
}
.workspace-state.error {
  color: var(--tone-danger-fg);
}
.workspace-state p {
  margin: 2px 0 0;
}
.pipeline-execution-layout {
  display: grid;
  grid-template-columns: minmax(520px, 0.9fr) minmax(420px, 1.1fr);
  gap: var(--space-4);
  align-items: start;
}
.pipeline-execution-inspector-scroll {
  position: sticky;
  top: var(--pipeline-studio-sticky-top, var(--space-3));
  max-height: var(--pipeline-studio-pane-max-height, min(76dvh, 960px));
  overflow: auto;
  overscroll-behavior: contain;
  border-radius: var(--radius-card);
}
.empty-state {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-card);
  color: var(--text-secondary);
}
.empty-state p {
  margin: 2px 0 0;
  font-size: 0.875rem;
}
@media (max-width: 1100px) {
  .pipeline-execution-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .pipeline-execution-inspector-scroll {
    position: static;
    max-height: none;
    overflow: visible;
  }
}
</style>
