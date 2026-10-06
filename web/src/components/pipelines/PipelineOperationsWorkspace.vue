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
import PipelineBenchmarkWorkspace from "./PipelineBenchmarkWorkspace.vue";
import PipelineComparisonWorkspace from "./PipelineComparisonWorkspace.vue";
import PipelineOperationsSummary from "./PipelineOperationsSummary.vue";
import UiButton from "../ui/UiButton.vue";
import UiTabs from "../ui/UiTabs.vue";
import type { PipelineOperationsSection } from "../../features/pipelines/composables/usePipelineStudioNavigation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelineOperationalMetrics,
  PipelinePurpose,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  operation: PipelineOperationsSection;
  pipelines: PipelineDefinition[];
  metrics: PipelineOperationalMetrics | null;
  strategies: PipelineStrategy[];
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  metricsPending: boolean;
  metricsRefreshing: boolean;
  metricsError: string;
}>();
const emit = defineEmits<{
  "update:operation": [section: PipelineOperationsSection];
  viewExecutions: [category: string];
  viewStrategy: [strategyId: string];
  openPipeline: [key: string];
  retryMetrics: [];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const tabs = computed(() => [
  { id: "health", label: t("pipelines.operations_health", "Health") },
  { id: "compare", label: t("pipelines.operations_compare", "Compare") },
  { id: "benchmarks", label: t("pipelines.operations_benchmarks", "Benchmarks") },
]);
</script>

<template>
  <section
    id="pipeline-panel-operations"
    class="pipeline-operations"
    role="tabpanel"
    aria-labelledby="pipeline-tab-operations"
  >
    <UiTabs
      :tabs="tabs"
      :model-value="props.operation"
      :tablist-label="t('pipelines.studio_operations', 'Operations')"
      id-prefix="pipeline-operations"
      @update:model-value="emit('update:operation', $event as PipelineOperationsSection)"
    />
    <div
      :id="`pipeline-operations-panel-${props.operation}`"
      role="tabpanel"
      :aria-labelledby="`pipeline-operations-tab-${props.operation}`"
    >
      <!-- Compare and Benchmarks keep their form and result while another tab is showing. -->
      <KeepAlive>
        <PipelineComparisonWorkspace
          v-if="props.operation === 'compare'"
          :pipelines="pipelines"
          @open-pipeline="emit('openPipeline', $event)"
        />
        <PipelineBenchmarkWorkspace
          v-else-if="props.operation === 'benchmarks'"
          :pipelines="pipelines"
          @open-pipeline="emit('openPipeline', $event)"
        />
      </KeepAlive>
      <div
        v-if="props.operation === 'health' && props.metricsPending"
        class="operation-state"
        role="status"
      >
        {{ t("pipelines.health_loading", "Loading operational health…") }}
      </div>
      <div
        v-else-if="props.operation === 'health' && props.metricsError && !metrics"
        class="operation-state error"
        role="alert"
      >
        <div>
          <strong>{{ t("pipelines.health_failed", "Could not load operational health.") }}</strong>
          <p>{{ props.metricsError }}</p>
        </div>
        <UiButton :label="t('common.retry', 'Retry')" @click="emit('retryMetrics')" />
      </div>
      <div
        v-if="props.operation === 'health' && props.metricsRefreshing && metrics"
        class="operation-state inline"
        role="status"
      >
        {{ t("loading.updating", "Updating…") }}
      </div>
      <div
        v-if="props.operation === 'health' && props.metricsError && metrics"
        class="operation-state error inline"
        role="alert"
      >
        <div>
          <strong>{{ t("loading.stale", "Showing previously loaded data.") }}</strong>
          <p>{{ props.metricsError }}</p>
        </div>
        <UiButton :label="t('common.retry', 'Retry')" @click="emit('retryMetrics')" />
      </div>
      <PipelineOperationsSummary
        v-if="props.operation === 'health' && metrics"
        :metrics="metrics"
        :strategies="strategies"
        :purposes="purposes"
        :vocabulary="vocabulary"
        @view-executions="emit('viewExecutions', $event)"
        @view-strategy="emit('viewStrategy', $event)"
      />
    </div>
  </section>
</template>

<style scoped>
.pipeline-operations {
  display: grid;
  gap: var(--space-4);
}
.operation-state {
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
.operation-state.inline {
  min-height: 0;
  padding-block: var(--space-2);
}
.operation-state.error {
  color: var(--tone-danger-fg);
}
.operation-state p {
  margin: 2px 0 0;
}
</style>
