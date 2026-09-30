<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import PipelineDefinitionHeader from "./PipelineDefinitionHeader.vue";
import PipelineGraphDiagram from "./PipelineGraphDiagram.vue";
import PipelineStageList from "./PipelineStageList.vue";
import PipelineWorkflowContract from "./PipelineWorkflowContract.vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAssignment,
  PipelineDefinition,
  PipelinePurpose,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

defineProps<{
  pipeline: PipelineDefinition;
  strategies: PipelineStrategy[];
  purpose: PipelinePurpose | null;
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  assignment: PipelineAssignment | null;
  assigned: boolean;
  canAssign: boolean;
  assigning: boolean;
  cloning: boolean;
}>();

const emit = defineEmits<{
  clone: [];
  assign: [];
  resetAssignment: [];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
</script>

<template>
  <article class="pipeline-detail">
    <PipelineDefinitionHeader
      :pipeline="pipeline"
      :purpose="purpose"
      :purposes="purposes"
      :vocabulary="vocabulary"
      :assignment="assignment"
      :assigned="assigned"
      :can-assign="canAssign"
      :assigning="assigning"
      :cloning="cloning"
      @clone="emit('clone')"
      @assign="emit('assign')"
      @reset-assignment="emit('resetAssignment')"
    />

    <PipelineWorkflowContract :pipeline="pipeline" :purpose="purpose" :vocabulary="vocabulary" />

    <div v-if="pipeline.runtime_support?.reason" class="support-note" data-tone="warning">
      <AppIcon name="help" />
      <span>{{ pipeline.runtime_support.reason }}</span>
    </div>
    <div
      v-if="
        pipeline.purpose === 'evidence_recovery' &&
        pipeline.runtime_support?.celf_compliant === false
      "
      class="support-note"
      data-tone="warning"
    >
      <AppIcon name="help" />
      <span>
        {{
          t(
            "pipelines.non_celf_boundary_help",
            "This pipeline keeps useful relevance suggestions, but does not guarantee direct support at its output. A reviewer can bind and validate direct evidence later; only that evidence-bound result receives a cELF guarantee.",
          )
        }}
      </span>
    </div>

    <ul
      v-if="pipeline.validation?.issues?.length"
      class="validation-issues"
      :aria-label="t('pipelines.validation_issues', 'Validation issues')"
    >
      <li
        v-for="issue in pipeline.validation.issues"
        :key="`${issue.code}:${issue.stage_id || ''}`"
        :data-level="issue.level"
      >
        <AppIcon :name="issue.level === 'error' ? 'warning' : 'help'" />
        <span>{{ issue.message }}</span>
      </li>
    </ul>

    <PipelineGraphDiagram
      :stages="pipeline.stages"
      :entry-stage-ids="pipeline.entry_stage_ids"
      :strategies="strategies"
      :vocabulary="vocabulary"
      :title="t('pipelines.diagram_title', 'Pipeline diagram')"
      :description="
        t(
          'pipelines.diagram_help',
          'Stages are nodes. Solid arrows are the normal path. Dashed arrows are fallbacks used only when a stage is empty, unavailable, timed out, or in error.',
        )
      "
    />

    <details class="stage-details">
      <summary>{{ t("pipelines.stage_details", "Stage details") }}</summary>
      <PipelineStageList :pipeline="pipeline" :strategies="strategies" :vocabulary="vocabulary" />
    </details>
  </article>
</template>

<style scoped>
.pipeline-detail {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.support-note,
.validation-issues li {
  display: flex;
  gap: var(--space-2);
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.support-note {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--tone-warn-edge);
  border-radius: var(--radius-control);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.support-note :deep(svg),
.validation-issues :deep(svg) {
  flex: 0 0 auto;
  width: 16px;
  height: 16px;
  margin-top: 2px;
}
.validation-issues {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--tone-warn-edge);
  border-radius: var(--radius-control);
  background: var(--tone-warn-bg);
  list-style: none;
}
.validation-issues li {
  color: var(--tone-warn-fg);
}
.validation-issues li[data-level="error"] {
  color: var(--tone-danger-fg);
}
.stage-details {
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--space-3);
}
.stage-details summary {
  width: fit-content;
  cursor: pointer;
  color: var(--text-primary);
  font-size: 0.9375rem;
  font-weight: var(--fw-bold);
}
.stage-details summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
</style>
