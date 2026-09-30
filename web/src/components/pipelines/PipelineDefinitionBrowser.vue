<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import { pipelineDefinitionStatusLabel, pipelineKey } from "../../domain/pipelinePresentation";
import {
  groupPipelinesByWorkflow,
  pipelineCategory,
  purposeById,
  purposeLabelFor,
  purposeText,
  termLabel,
} from "../../domain/pipelineWorkflows";
import type {
  PipelineAssignment,
  PipelineDefinition,
  PipelinePurpose,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  pipelines: PipelineDefinition[];
  assignments: PipelineAssignment[];
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  selectedKey: string;
  /** Selected workflow category ID; empty for all workflows. */
  workflow?: string;
}>();

const emit = defineEmits<{
  select: [key: string];
  "update:workflow": [category: string];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const query = ref("");
const status = ref("");

const categoryLabels = computed(
  () => new Map(props.vocabulary.categories.map((term) => [term.id, termLabel(term, t)])),
);

function searchText(pipeline: PipelineDefinition) {
  const purpose = purposeById(props.purposes, pipeline.purpose);
  return [
    pipeline.name,
    pipeline.pipeline_id,
    pipeline.purpose,
    String(pipeline.version),
    purpose ? purposeText(purpose, "label", t) : "",
    categoryLabels.value.get(pipelineCategory(pipeline, props.purposes)) || "",
  ]
    .join(" ")
    .toLowerCase();
}

const matching = computed(() => {
  const needle = query.value.trim().toLowerCase();
  return props.pipelines.filter((pipeline) => {
    if (status.value && pipeline.status !== status.value) return false;
    return !needle || searchText(pipeline).includes(needle);
  });
});

const counts = computed(() => {
  const values = new Map<string, number>();
  for (const pipeline of matching.value) {
    const category = pipelineCategory(pipeline, props.purposes);
    values.set(category, (values.get(category) || 0) + 1);
  }
  return values;
});

const grouped = computed(() => {
  const visible = props.workflow
    ? matching.value.filter(
        (pipeline) => pipelineCategory(pipeline, props.purposes) === props.workflow,
      )
    : matching.value;
  return groupPipelinesByWorkflow(visible, props.purposes, props.vocabulary);
});

const visibleCount = computed(
  () =>
    grouped.value.groups.reduce((sum, group) => sum + group.pipelines.length, 0) +
    grouped.value.unclassified.length,
);

function assigned(pipeline: PipelineDefinition) {
  return props.assignments.some(
    (item) =>
      item.pipeline_id === pipeline.pipeline_id && item.pipeline_version === pipeline.version,
  );
}

function chooseWorkflow(category: string) {
  emit("update:workflow", category);
}
</script>

<template>
  <aside class="pipeline-browser" :aria-label="t('pipelines.definitions', 'Pipeline definitions')">
    <div class="browser-heading">
      <strong class="heading-with-help">
        {{ t("pipelines.definitions", "Pipeline definitions") }}
        <UiTooltip
          :text="
            t(
              'pipelines.definitions_help',
              'Each row is one immutable pipeline version. Several rows can share the same pipeline ID because version history is preserved rather than overwritten.',
            )
          "
        />
      </strong>
      <span :aria-label="t('pipelines.definition_count', 'Pipeline definition count')">
        {{ visibleCount }}/{{ pipelines.length }}
      </span>
    </div>

    <form class="browser-filters" @submit.prevent>
      <label>
        <span class="sr-only">{{ t("pipelines.search_definitions", "Search pipelines") }}</span>
        <input
          v-model="query"
          class="control"
          type="search"
          :placeholder="t('pipelines.search_definitions', 'Search pipelines')"
          :aria-label="t('pipelines.search_definitions', 'Search pipelines')"
        />
      </label>
      <div class="workflow-filter" role="group" :aria-label="t('pipelines.used_for', 'Used for')">
        <span class="filter-label" aria-hidden="true">{{
          t("pipelines.used_for", "Used for")
        }}</span>
        <button
          type="button"
          class="workflow-option"
          :aria-pressed="!workflow"
          @click="chooseWorkflow('')"
        >
          {{ t("pipelines.filter_all", "All") }}
          <span class="option-count">{{ matching.length }}</span>
        </button>
        <button
          v-for="category in vocabulary.categories"
          :key="category.id"
          type="button"
          class="workflow-option"
          :data-category="category.id"
          :aria-pressed="workflow === category.id"
          @click="chooseWorkflow(category.id)"
        >
          {{ termLabel(category, t) }}
          <span class="option-count">{{ counts.get(category.id) || 0 }}</span>
        </button>
      </div>
      <label>
        <span class="sr-only">{{ t("pipelines.filter_status", "Status") }}</span>
        <select
          v-model="status"
          class="control"
          :aria-label="t('pipelines.filter_status', 'Status')"
        >
          <option value="">{{ t("pipelines.filter_all_statuses", "All statuses") }}</option>
          <option value="active">{{ t("pipelines.status_active", "Active") }}</option>
          <option value="draft">{{ t("pipelines.status_draft", "Draft") }}</option>
          <option value="disabled">{{ t("pipelines.status_disabled", "Disabled") }}</option>
        </select>
      </label>
    </form>

    <p v-if="!visibleCount" class="browser-empty">
      {{ t("pipelines.no_definition_matches", "No pipelines match these filters.") }}
    </p>
    <section
      v-for="group in grouped.groups"
      :key="group.category.id"
      class="workflow-group"
      :data-category="group.category.id"
      :aria-labelledby="`pipeline-workflow-${group.category.id}`"
    >
      <h3 :id="`pipeline-workflow-${group.category.id}`" class="group-heading">
        {{ termLabel(group.category, t) }}
      </h3>
      <button
        v-for="pipeline in group.pipelines"
        :key="pipelineKey(pipeline)"
        type="button"
        class="pipeline-choice"
        :class="{ selected: selectedKey === pipelineKey(pipeline) }"
        :aria-current="selectedKey === pipelineKey(pipeline) ? 'true' : undefined"
        @click="emit('select', pipelineKey(pipeline))"
      >
        <span class="choice-top">
          <strong>{{ pipeline.name }}</strong>
          <small>v{{ pipeline.version }}</small>
        </span>
        <span class="choice-meta">
          {{ purposeLabelFor(purposes, pipeline.purpose, t) }}
          <span aria-hidden="true">·</span>
          {{ pipelineDefinitionStatusLabel(pipeline.status, t) }}
        </span>
        <span v-if="pipeline.built_in || assigned(pipeline)" class="choice-badges">
          <span v-if="pipeline.built_in" class="choice-badge">
            {{ t("pipelines.built_in", "Built in") }}
          </span>
          <span v-if="assigned(pipeline)" class="choice-badge active">
            {{ t("pipelines.assigned", "Assigned") }}
          </span>
        </span>
      </button>
    </section>
    <section
      v-if="grouped.unclassified.length && !workflow"
      class="workflow-group"
      aria-labelledby="pipeline-workflow-unclassified"
    >
      <h3 id="pipeline-workflow-unclassified" class="group-heading">
        {{ t("pipelines.unregistered_purpose", "Unregistered purpose") }}
      </h3>
      <button
        v-for="pipeline in grouped.unclassified"
        :key="pipelineKey(pipeline)"
        type="button"
        class="pipeline-choice"
        :class="{ selected: selectedKey === pipelineKey(pipeline) }"
        :aria-current="selectedKey === pipelineKey(pipeline) ? 'true' : undefined"
        @click="emit('select', pipelineKey(pipeline))"
      >
        <span class="choice-top">
          <strong>{{ pipeline.name }}</strong>
          <small>v{{ pipeline.version }}</small>
        </span>
        <span class="choice-meta"
          ><code>{{ pipeline.purpose }}</code></span
        >
      </button>
    </section>
  </aside>
</template>

<style scoped>
.pipeline-browser {
  align-self: start;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.browser-heading {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid var(--line);
}
.browser-heading span {
  color: var(--muted);
  font-size: 0.78rem;
}
.browser-filters {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
}
.workflow-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}
.filter-label {
  width: 100%;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.workflow-option {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 30px;
  padding: 3px 9px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 0.76rem;
  cursor: pointer;
}
.workflow-option[aria-pressed="true"] {
  border-color: currentColor;
  background: var(--soft);
  font-weight: 750;
}
.workflow-option:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}
.option-count {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.workflow-group {
  border-bottom: 1px solid var(--line);
}
.workflow-group:last-child {
  border-bottom: 0;
}
.group-heading {
  margin: 0;
  padding: 10px 12px 4px;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.browser-filters .control {
  width: 100%;
  min-height: 36px;
}
.browser-empty {
  margin: 0;
  padding: 12px;
  color: var(--muted);
  font-size: 0.78rem;
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
.heading-with-help {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.pipeline-choice {
  position: relative;
  display: grid;
  gap: 4px;
  width: 100%;
  min-height: 44px;
  padding: 12px;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.pipeline-choice:last-child {
  border-bottom: 0;
}
.choice-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.pipeline-choice:hover,
.pipeline-choice.selected {
  background: var(--soft);
}
.pipeline-choice:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: -2px;
}
.pipeline-choice.selected::before {
  position: absolute;
  inset: 8px auto 8px 0;
  width: 3px;
  border-radius: 999px;
  background: currentColor;
  content: "";
}
.choice-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.choice-top strong {
  font-size: 0.82rem;
}
.choice-top small,
.choice-meta,
.choice-badge {
  font-size: 0.75rem;
}
.choice-top small,
.choice-meta,
.choice-badge {
  color: var(--muted);
}
.choice-badge {
  margin-top: 3px;
  padding: 2px 6px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-weight: 750;
}
.choice-badge.active {
  color: inherit;
}
@media (max-width: 960px) {
  .pipeline-browser {
    max-height: 300px;
    overflow: auto;
  }
}
</style>
