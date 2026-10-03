<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import PipelineTypeChip from "./PipelineTypeChip.vue";
import {
  pipelineComputationLabel,
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
  <div
    class="strategy-table-scroll"
    role="region"
    tabindex="0"
    :aria-label="t('pipelines.strategies_title', 'Strategies')"
  >
    <table class="strategy-table">
      <caption class="sr-only">
        {{
          t("pipelines.strategies_title", "Strategies")
        }}
      </caption>
      <colgroup>
        <col class="column-strategy" />
        <col class="column-family" />
        <col class="column-flow" />
        <col class="column-usage" />
      </colgroup>
      <thead>
        <tr>
          <th scope="col" data-column="strategy">
            <span class="stacked-heading">
              <span>{{ t("pipelines.strategy_column", "Strategy") }}</span>
              <small>{{ t("pipelines.scholarly_effect", "Scholarly effect") }}</small>
            </span>
          </th>
          <th scope="col" data-column="family">
            <span class="stacked-heading">
              <span>{{ t("pipelines.strategy_family", "Family") }}</span>
              <small>{{ t("pipelines.strategy_computation", "Computation") }}</small>
            </span>
          </th>
          <th scope="col" data-column="flow">
            {{ t("pipelines.strategy_input_output", "Input → output") }}
          </th>
          <th scope="col" data-column="usage" class="numeric">
            {{ t("pipelines.strategy_used_by", "Used by") }}
          </th>
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
          <th scope="row" data-column="strategy">
            <div class="strategy-identity">
              <button
                type="button"
                class="row-select"
                :aria-current="strategy.strategy_id === selectedId ? 'true' : undefined"
                @click.stop="emit('select', strategy.strategy_id)"
              >
                <strong>{{ pipelineStrategyLabel(strategy, t) }}</strong>
                <code>{{ strategy.strategy_id }}</code>
              </button>
              <span v-if="effectLabel(strategy)" class="strategy-effect">
                {{ effectLabel(strategy) }}
              </span>
            </div>
          </th>
          <td data-column="family">
            <strong class="family-label">{{ pipelineStageFamilyLabel(strategy.family, t) }}</strong>
            <span class="computation-label">
              {{ pipelineComputationLabel(strategyComputation(strategy), t) }}
            </span>
          </td>
          <td data-column="flow">
            <div class="data-flow">
              <PipelineTypeChip :type="strategy.input_type" />
              <span class="data-flow-arrow" aria-hidden="true">→</span>
              <span class="sr-only">{{ t("pipelines.to", "to") }}</span>
              <PipelineTypeChip :type="strategy.output_type" />
            </div>
          </td>
          <td data-column="usage" class="numeric usage-count">
            <strong>{{ usedBy(strategy) }}</strong>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.strategy-table-scroll {
  position: sticky;
  top: var(--pipeline-studio-sticky-top, var(--space-3));
  max-height: var(--pipeline-studio-pane-max-height, min(76dvh, 960px));
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.strategy-table-scroll:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.strategy-table {
  width: 100%;
  min-width: 760px;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.875rem;
}
.strategy-table col.column-strategy {
  width: 42%;
}
.strategy-table col.column-family {
  width: 22%;
}
.strategy-table col.column-flow {
  width: 27%;
}
.strategy-table col.column-usage {
  width: 9%;
}
.strategy-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 10px var(--space-3);
  border-bottom: 1px solid var(--border-strong);
  background: var(--surface-card);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
  line-height: 1.2;
  text-align: left;
  vertical-align: bottom;
}
.strategy-table thead th[data-column="strategy"] {
  left: 0;
  z-index: 3;
  box-shadow: 1px 0 0 var(--border-subtle);
}
.stacked-heading {
  display: grid;
  gap: 2px;
}
.stacked-heading small {
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 400;
}
.strategy-table td,
.strategy-table tbody th {
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-card);
  color: var(--text-secondary);
  text-align: left;
  vertical-align: middle;
}
.strategy-table tbody th[data-column="strategy"] {
  position: sticky;
  left: 0;
  z-index: 1;
  box-shadow: 1px 0 0 var(--border-subtle);
}
.strategy-table tbody tr {
  cursor: pointer;
}
.strategy-table tbody tr:hover > *,
.strategy-table tbody tr.selected > * {
  background: var(--surface-selected);
}
.strategy-table tbody tr.selected > th[data-column="strategy"] {
  box-shadow:
    inset 3px 0 0 var(--accent),
    1px 0 0 var(--border-subtle);
}
.strategy-table tbody tr:last-child > * {
  border-bottom: 0;
}
.strategy-table .numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.strategy-identity {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}
.row-select {
  display: grid;
  gap: 2px;
  width: 100%;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.row-select strong,
.family-label {
  color: var(--text-primary);
  line-height: 1.3;
}
.row-select code {
  overflow: hidden;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row-select:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.strategy-effect {
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 400;
  line-height: 1.35;
}
.family-label,
.computation-label {
  display: block;
}
.computation-label {
  margin-top: 3px;
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.data-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
}
.data-flow-arrow {
  color: var(--text-tertiary);
  font-weight: var(--fw-bold);
}
.usage-count {
  color: var(--text-primary);
  font-size: 0.9375rem;
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

@media (max-width: 1120px) {
  .strategy-table-scroll {
    position: static;
    max-height: none;
  }
}
</style>
