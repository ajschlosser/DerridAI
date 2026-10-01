<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import PipelineStrategyFilters from "./PipelineStrategyFilters.vue";
import PipelineStrategyInspector from "./PipelineStrategyInspector.vue";
import PipelineStrategyTable from "./PipelineStrategyTable.vue";
import type { PipelineStrategyFilters as StrategyFilters } from "../../features/pipelines/composables/usePipelineStudioNavigation";
import {
  pipelineStageFamilyLabel,
  pipelineStrategyDescription,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import { strategyComputation, strategyUsage } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelinePurpose,
  PipelineStrategy,
  PipelineStrategyLatency,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  strategies: PipelineStrategy[];
  pipelines: PipelineDefinition[];
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  selectedStrategyId: string;
  filters: StrategyFilters;
  /** Observed latency per strategy from recent runs, when available. */
  strategyLatency?: Record<string, PipelineStrategyLatency> | null;
}>();
const emit = defineEmits<{
  selectStrategy: [id: string];
  openPipeline: [key: string];
  "update:filters": [filters: StrategyFilters];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const usage = computed(
  () =>
    new Map(
      props.strategies.map((item) => [
        item.strategy_id,
        strategyUsage(item.strategy_id, props.pipelines, props.purposes, props.vocabulary),
      ]),
    ),
);

function matchesQuery(strategy: PipelineStrategy, needle: string) {
  return [
    strategy.strategy_id,
    strategy.label,
    pipelineStrategyLabel(strategy, t),
    strategy.description,
    pipelineStrategyDescription(strategy, t),
    pipelineStageFamilyLabel(strategy.family, t),
    ...strategy.capabilities,
  ]
    .join(" ")
    .toLowerCase()
    .includes(needle);
}

const visible = computed(() => {
  const { query, family, computation, capability, effect, workflow } = props.filters;
  const needle = query.trim().toLowerCase();
  return props.strategies.filter((strategy) => {
    if (family && strategy.family !== family) return false;
    if (computation && strategyComputation(strategy) !== computation) return false;
    if (capability && !strategy.capabilities.includes(capability)) return false;
    if (effect && strategy.scholarly_effect !== effect) return false;
    if (workflow && !usage.value.get(strategy.strategy_id)?.categories.includes(workflow)) {
      return false;
    }
    return !needle || matchesQuery(strategy, needle);
  });
});
// The route keeps the chosen strategy; before one is chosen the first row is shown.
const selected = computed(
  () =>
    visible.value.find((item) => item.strategy_id === props.selectedStrategyId) ||
    visible.value[0] ||
    null,
);
</script>

<template>
  <section
    id="pipeline-panel-strategies"
    class="strategies-workspace"
    role="tabpanel"
    aria-labelledby="pipeline-tab-strategies"
  >
    <header class="workspace-heading">
      <h2>{{ t("pipelines.strategies_title", "Strategies") }}</h2>
      <p>
        {{
          t(
            "pipelines.strategies_help",
            "Every operation a pipeline stage can run. One strategy can serve several workflows; its scholarly effect says what, if anything, it establishes about evidence or support.",
          )
        }}
      </p>
    </header>

    <PipelineStrategyFilters
      :filters="filters"
      :strategies="strategies"
      :vocabulary="vocabulary"
      :shown="visible.length"
      @update:filters="emit('update:filters', $event)"
    />

    <p v-if="!visible.length" class="workspace-empty">
      {{ t("pipelines.no_strategy_matches", "No strategies match these filters.") }}
    </p>
    <div v-else class="strategies-layout">
      <PipelineStrategyTable
        :strategies="visible"
        :usage="usage"
        :vocabulary="vocabulary"
        :selected-id="selected?.strategy_id || ''"
        @select="emit('selectStrategy', $event)"
      />
      <PipelineStrategyInspector
        v-if="selected"
        :strategy="selected"
        :usage="usage.get(selected.strategy_id) || { pipelines: [], categories: [] }"
        :purposes="purposes"
        :vocabulary="vocabulary"
        :latency="strategyLatency?.[selected.strategy_id] ?? null"
        @open-pipeline="emit('openPipeline', $event)"
      />
    </div>
  </section>
</template>

<style scoped>
.strategies-workspace {
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
.workspace-empty {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.875rem;
}
.strategies-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.9fr);
  gap: var(--space-4);
  align-items: start;
}
@media (max-width: 960px) {
  .strategies-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
