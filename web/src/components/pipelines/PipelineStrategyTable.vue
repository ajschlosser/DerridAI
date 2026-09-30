<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import {
  pipelineComputationLabel,
  pipelineDataTypeLabel,
  pipelineStageFamilyLabel,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import {
  findTerm,
  strategyComputation,
  termLabel,
  type StrategyUsage,
} from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineStrategy, PipelineWorkflowVocabulary } from "../../types/pipelines";

const props = defineProps<{
  strategies: PipelineStrategy[];
  usage: Map<string, StrategyUsage>;
  vocabulary: PipelineWorkflowVocabulary;
  selectedId: string;
}>();
const emit = defineEmits<{ select: [strategyId: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

function effectLabel(strategy: PipelineStrategy) {
  const term = findTerm(props.vocabulary.effect_notes, strategy.effect_note);
  return term ? termLabel(term, t) : "";
}
function usedBy(strategy: PipelineStrategy) {
  return props.usage.get(strategy.strategy_id)?.pipelines.length ?? 0;
}
</script>

<template>
  <div class="strategy-table-scroll">
    <table class="strategy-table">
      <caption class="sr-only">
        {{
          t("pipelines.strategies_title", "Strategies")
        }}
      </caption>
      <thead>
        <tr>
          <th scope="col">{{ t("pipelines.strategy_column", "Strategy") }}</th>
          <th scope="col">{{ t("pipelines.strategy_family", "Family") }}</th>
          <th scope="col">{{ t("pipelines.strategy_computation", "Computation") }}</th>
          <th scope="col">{{ t("pipelines.strategy_input_output", "Input → output") }}</th>
          <th scope="col">{{ t("pipelines.scholarly_effect", "Scholarly effect") }}</th>
          <th scope="col" class="numeric">{{ t("pipelines.strategy_used_by", "Used by") }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="strategy in strategies"
          :key="strategy.strategy_id"
          :data-strategy="strategy.strategy_id"
          :class="{ selected: strategy.strategy_id === selectedId }"
          @click="emit('select', strategy.strategy_id)"
        >
          <th scope="row">
            <button
              type="button"
              class="row-select"
              :aria-current="strategy.strategy_id === selectedId ? 'true' : undefined"
              @click.stop="emit('select', strategy.strategy_id)"
            >
              <strong>{{ pipelineStrategyLabel(strategy, t) }}</strong>
              <code>{{ strategy.strategy_id }}</code>
            </button>
          </th>
          <td>{{ pipelineStageFamilyLabel(strategy.family, t) }}</td>
          <td>{{ pipelineComputationLabel(strategyComputation(strategy), t) }}</td>
          <td>
            {{ pipelineDataTypeLabel(strategy.input_type, t) }} →
            {{ pipelineDataTypeLabel(strategy.output_type, t) }}
          </td>
          <td>{{ effectLabel(strategy) }}</td>
          <td class="numeric">{{ usedBy(strategy) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.strategy-table-scroll {
  max-height: min(76dvh, 960px);
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.strategy-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
.strategy-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-strong);
  background: var(--surface-card);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
  text-align: left;
  white-space: nowrap;
}
.strategy-table td,
.strategy-table tbody th {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  text-align: left;
  vertical-align: top;
}
.strategy-table tbody tr {
  cursor: pointer;
}
.strategy-table tbody tr:hover,
.strategy-table tbody tr.selected {
  background: var(--surface-selected);
}
.strategy-table .numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.row-select {
  display: grid;
  gap: 2px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.row-select code {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.row-select:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
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
</style>
