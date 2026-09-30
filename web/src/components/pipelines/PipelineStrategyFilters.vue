<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import PipelineFilterBar from "./PipelineFilterBar.vue";
import type { PipelineStrategyFilters } from "../../features/pipelines/composables/usePipelineStudioNavigation";
import {
  pipelineCapabilityLabel,
  pipelineComputationLabel,
  pipelineStageFamilyLabel,
} from "../../domain/pipelinePresentation";
import { termLabel, type StrategyComputation } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineStrategy, PipelineWorkflowVocabulary } from "../../types/pipelines";

const props = defineProps<{
  filters: PipelineStrategyFilters;
  strategies: PipelineStrategy[];
  vocabulary: PipelineWorkflowVocabulary;
  shown: number;
}>();
const emit = defineEmits<{ "update:filters": [filters: PipelineStrategyFilters] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const computations: StrategyComputation[] = ["deterministic", "learned", "generative"];
const families = computed(() => [...new Set(props.strategies.map((item) => item.family))]);
const capabilities = computed(() =>
  [...new Set(props.strategies.flatMap((item) => item.capabilities))].sort(),
);
const advancedCount = computed(
  () =>
    [props.filters.computation, props.filters.capability, props.filters.workflow].filter(Boolean)
      .length,
);
const active = computed(() => Object.values(props.filters).some(Boolean));

function update(patch: Partial<PipelineStrategyFilters>) {
  emit("update:filters", { ...props.filters, ...patch });
}
function value(event: Event) {
  return (event.target as HTMLInputElement | HTMLSelectElement).value;
}
</script>

<template>
  <PipelineFilterBar
    :label="t('pipelines.filter_strategies', 'Filter strategies')"
    has-advanced
    :advanced-count="advancedCount"
    :can-reset="active"
    :result-label="
      i18n.tf('pipelines.strategy_count', '{shown} of {total} strategies', {
        shown,
        total: strategies.length,
      })
    "
    @reset="
      emit('update:filters', {
        query: '',
        family: '',
        computation: '',
        capability: '',
        effect: '',
        workflow: '',
      })
    "
  >
    <template #search>
      <label>
        <span>{{ t("pipelines.search_strategies", "Search strategies") }}</span>
        <input
          class="control"
          type="search"
          autocomplete="off"
          :value="filters.query"
          @input="update({ query: value($event) })"
        />
      </label>
    </template>
    <template #primary>
      <label>
        <span>{{ t("pipelines.strategy_family", "Family") }}</span>
        <select class="control" :value="filters.family" @change="update({ family: value($event) })">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="item in families" :key="item" :value="item">
            {{ pipelineStageFamilyLabel(item, t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.scholarly_effect", "Scholarly effect") }}</span>
        <select class="control" :value="filters.effect" @change="update({ effect: value($event) })">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="term in vocabulary.scholarly_effects" :key="term.id" :value="term.id">
            {{ termLabel(term, t) }}
          </option>
        </select>
      </label>
    </template>
    <template #advanced>
      <label>
        <span>{{ t("pipelines.strategy_computation", "Computation") }}</span>
        <select
          class="control"
          :value="filters.computation"
          @change="update({ computation: value($event) })"
        >
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="item in computations" :key="item" :value="item">
            {{ pipelineComputationLabel(item, t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.strategy_requires", "Requires") }}</span>
        <select
          class="control"
          :value="filters.capability"
          @change="update({ capability: value($event) })"
        >
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="item in capabilities" :key="item" :value="item">
            {{ pipelineCapabilityLabel(item, t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.strategy_used_by", "Used by") }}</span>
        <select
          class="control"
          :value="filters.workflow"
          @change="update({ workflow: value($event) })"
        >
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="term in vocabulary.categories" :key="term.id" :value="term.id">
            {{ termLabel(term, t) }}
          </option>
        </select>
      </label>
    </template>
  </PipelineFilterBar>
</template>
