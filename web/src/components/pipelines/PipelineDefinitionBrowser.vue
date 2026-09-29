<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import {
  pipelineDefinitionStatusLabel,
  pipelineKey,
  pipelinePurposeLabel,
} from "../../domain/pipelinePresentation";
import type { PipelineAssignment, PipelineDefinition } from "../../types/pipelines";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  pipelines: PipelineDefinition[];
  assignments: PipelineAssignment[];
  selectedKey: string;
}>();

const emit = defineEmits<{
  select: [key: string];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

function assigned(pipeline: PipelineDefinition) {
  return props.assignments.some(
    (item) =>
      item.pipeline_id === pipeline.pipeline_id && item.pipeline_version === pipeline.version,
  );
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
        {{ pipelines.length }}
      </span>
    </div>

    <button
      v-for="pipeline in pipelines"
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
        {{ pipelinePurposeLabel(pipeline.purpose, t) }}
        <span aria-hidden="true">·</span>
        {{ pipelineDefinitionStatusLabel(pipeline.status, t) }}
      </span>
      <span v-if="pipeline.built_in" class="choice-badge">
        {{ t("pipelines.built_in", "Built in") }}
      </span>
      <span v-if="assigned(pipeline)" class="choice-badge active">
        {{ t("pipelines.assigned", "Assigned") }}
      </span>
    </button>
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
  justify-self: start;
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
