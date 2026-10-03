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
}>();
const emit = defineEmits<{
  "update:operation": [section: PipelineOperationsSection];
  viewExecutions: [category: string];
  viewStrategy: [strategyId: string];
  openPipeline: [key: string];
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
</style>
