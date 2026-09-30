<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import PipelineStrategyCard from "./PipelineStrategyCard.vue";
import {
  pipelineCapabilityLabel,
  pipelineComputationLabel,
  pipelineStageFamilyLabel,
  pipelineStrategyDescription,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import {
  strategyComputation,
  strategyUsage,
  termLabel,
  type StrategyComputation,
} from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelinePurpose,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  strategies: PipelineStrategy[];
  pipelines: PipelineDefinition[];
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  selectedStrategyId?: string;
}>();

const emit = defineEmits<{
  selectStrategy: [strategyId: string];
  openPipeline: [key: string];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const query = ref("");
const family = ref("");
const computation = ref<StrategyComputation | "">("");
const capability = ref("");
const effect = ref("");
const workflow = ref("");

const computations: StrategyComputation[] = ["deterministic", "learned", "generative"];
const families = computed(() => [...new Set(props.strategies.map((item) => item.family))]);
const capabilities = computed(() =>
  [...new Set(props.strategies.flatMap((item) => item.capabilities))].sort(),
);
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
  const needle = query.value.trim().toLowerCase();
  return props.strategies.filter((strategy) => {
    if (family.value && strategy.family !== family.value) return false;
    if (computation.value && strategyComputation(strategy) !== computation.value) return false;
    if (capability.value && !strategy.capabilities.includes(capability.value)) return false;
    if (effect.value && strategy.scholarly_effect !== effect.value) return false;
    if (
      workflow.value &&
      !usage.value.get(strategy.strategy_id)?.categories.includes(workflow.value)
    ) {
      return false;
    }
    return !needle || matchesQuery(strategy, needle);
  });
});

function resetFilters() {
  query.value = "";
  family.value = "";
  computation.value = "";
  capability.value = "";
  effect.value = "";
  workflow.value = "";
}
</script>

<template>
  <section class="strategy-catalog" aria-labelledby="pipeline-strategies-title">
    <header class="catalog-heading">
      <h3 id="pipeline-strategies-title">{{ t("pipelines.strategies_title", "Strategies") }}</h3>
      <p>
        {{
          t(
            "pipelines.strategies_help",
            "Every operation a pipeline stage can run. One strategy can serve several workflows; its scholarly effect says what, if anything, it establishes about evidence or support.",
          )
        }}
      </p>
    </header>

    <form class="catalog-filters" @submit.prevent>
      <label class="filter-search">
        <span>{{ t("pipelines.search_strategies", "Search strategies") }}</span>
        <input v-model="query" class="control" type="search" autocomplete="off" />
      </label>
      <label>
        <span>{{ t("pipelines.strategy_family", "Family") }}</span>
        <select v-model="family" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="item in families" :key="item" :value="item">
            {{ pipelineStageFamilyLabel(item, t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.strategy_computation", "Computation") }}</span>
        <select v-model="computation" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="item in computations" :key="item" :value="item">
            {{ pipelineComputationLabel(item, t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.strategy_requires", "Requires") }}</span>
        <select v-model="capability" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="item in capabilities" :key="item" :value="item">
            {{ pipelineCapabilityLabel(item, t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.scholarly_effect", "Scholarly effect") }}</span>
        <select v-model="effect" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="term in vocabulary.scholarly_effects" :key="term.id" :value="term.id">
            {{ termLabel(term, t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.strategy_used_by", "Used by") }}</span>
        <select v-model="workflow" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="term in vocabulary.categories" :key="term.id" :value="term.id">
            {{ termLabel(term, t) }}
          </option>
        </select>
      </label>
      <button class="btn" type="button" @click="resetFilters">
        {{ t("pipelines.reset_filters", "Reset") }}
      </button>
    </form>

    <p class="result-count" role="status">
      {{
        i18n.tf("pipelines.strategy_count", "{shown} of {total} strategies", {
          shown: visible.length,
          total: strategies.length,
        })
      }}
    </p>

    <p v-if="!visible.length" class="catalog-empty">
      {{ t("pipelines.no_strategy_matches", "No strategies match these filters.") }}
    </p>
    <div v-else class="strategy-grid">
      <PipelineStrategyCard
        v-for="strategy in visible"
        :key="strategy.strategy_id"
        :strategy="strategy"
        :usage="usage.get(strategy.strategy_id) || { pipelines: [], categories: [] }"
        :purposes="purposes"
        :vocabulary="vocabulary"
        :selected="selectedStrategyId === strategy.strategy_id"
        @select="emit('selectStrategy', $event)"
        @open-pipeline="emit('openPipeline', $event)"
      />
    </div>
  </section>
</template>

<style scoped>
.strategy-catalog {
  display: grid;
  gap: 12px;
}
.catalog-heading h3 {
  margin: 0;
  font-size: 1rem;
}
.catalog-heading p {
  max-width: 780px;
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.8rem;
  line-height: 1.5;
}
.catalog-filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  align-items: end;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
}
.catalog-filters label {
  display: grid;
  gap: 3px;
  font-size: 0.75rem;
  font-weight: 750;
}
.filter-search {
  grid-column: span 2;
}
.catalog-filters .control {
  width: 100%;
  min-height: 36px;
}
.result-count,
.catalog-empty {
  margin: 0;
  color: var(--muted);
  font-size: 0.78rem;
}
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 380px), 1fr));
  gap: 10px;
}
@media (max-width: 680px) {
  .filter-search {
    grid-column: auto;
  }
}
</style>
