<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import PipelineStageList from "./PipelineStageList.vue";
import { pipelinePurposeLabel } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAssignment,
  PipelineDefinition,
  PipelineStrategy,
} from "../../types/pipelines";

defineProps<{
  pipeline: PipelineDefinition;
  strategies: PipelineStrategy[];
  assignment: PipelineAssignment | null;
  assigned: boolean;
  canAssign: boolean;
  assigning: boolean;
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
    <header class="detail-header">
      <div>
        <div class="detail-kicker">{{ pipelinePurposeLabel(pipeline.purpose, t) }}</div>
        <h3>{{ pipeline.name }}</h3>
        <p>
          <code>{{ pipeline.pipeline_id }}@{{ pipeline.version }}</code>
          <span v-if="pipeline.derived_from">
            · {{ t("pipelines.derived_from", "derived from") }}
            <code>{{ pipeline.derived_from }}</code>
          </span>
        </p>
      </div>
      <div class="detail-actions">
        <button class="btn" type="button" @click="emit('clone')">
          <AppIcon name="copy" />
          {{ t("pipelines.clone", "Clone & edit") }}
        </button>
        <button
          class="btn primary"
          type="button"
          :disabled="!canAssign || assigned || assigning"
          @click="emit('assign')"
        >
          <AppIcon name="check" />
          {{
            assigned
              ? t("pipelines.active_assignment", "Active assignment")
              : t("pipelines.assign", "Make active")
          }}
        </button>
      </div>
    </header>

    <dl class="health-strip">
      <div>
        <dt>{{ t("pipelines.graph_validation", "Graph validation") }}</dt>
        <dd>
          {{
            pipeline.validation?.valid === false
              ? t("pipelines.invalid", "Invalid")
              : t("pipelines.valid", "Valid")
          }}
        </dd>
      </div>
      <div>
        <dt>{{ t("pipelines.runtime_support", "Runtime support") }}</dt>
        <dd>
          {{
            pipeline.runtime_support?.supported
              ? t("pipelines.executable", "Executable")
              : t("pipelines.inspect_only", "Inspect only")
          }}
        </dd>
      </div>
      <div>
        <dt>{{ t("pipelines.assignment", "Assignment") }}</dt>
        <dd>
          {{
            assigned
              ? t("pipelines.assigned", "Assigned")
              : t("pipelines.not_assigned", "Not assigned")
          }}
        </dd>
      </div>
    </dl>

    <p v-if="pipeline.runtime_support?.reason" class="support-note">
      <AppIcon name="help" />
      <span>{{ pipeline.runtime_support.reason }}</span>
    </p>

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

    <PipelineStageList :pipeline="pipeline" :strategies="strategies" />

    <footer v-if="assignment && assignment.source !== 'built_in'" class="assignment-footer">
      <div>
        <strong>{{ t("pipelines.custom_assignment", "Custom system assignment") }}</strong>
        <span>
          {{ assignment.feature }} · {{ assignment.pipeline_id }}@{{ assignment.pipeline_version }}
        </span>
      </div>
      <button
        class="btn"
        type="button"
        :disabled="assigning"
        @click="emit('resetAssignment')"
      >
        {{ t("pipelines.restore_default", "Restore built-in default") }}
      </button>
    </footer>
  </article>
</template>

<style scoped>
.pipeline-detail {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.detail-header,
.assignment-footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.detail-kicker {
  margin-bottom: 3px;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.detail-header h3 {
  margin: 0;
  font-size: 1rem;
}
.detail-header p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.76rem;
}
.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.detail-actions :deep(svg),
.support-note :deep(svg),
.validation-issues :deep(svg) {
  width: 15px;
  height: 15px;
}
.health-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  overflow: hidden;
  margin: 0;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.health-strip > div {
  display: grid;
  gap: 3px;
  padding: 9px 10px;
  border-right: 1px solid var(--line);
}
.health-strip > div:last-child {
  border-right: 0;
}
.health-strip dt {
  color: var(--muted);
  font-size: 0.75rem;
}
.health-strip dd {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 700;
}
.support-note {
  display: flex;
  gap: 8px;
  margin: 0;
  color: var(--muted);
  font-size: 0.77rem;
  line-height: 1.45;
}
.support-note :deep(svg) {
  flex: 0 0 auto;
  margin-top: 1px;
}
.validation-issues {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.validation-issues li {
  display: flex;
  gap: 7px;
  color: var(--muted);
  font-size: 0.76rem;
}
.validation-issues li[data-level="error"] {
  color: inherit;
}
.assignment-footer {
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
.assignment-footer > div {
  display: grid;
  gap: 2px;
}
.assignment-footer strong {
  font-size: 0.8rem;
}
.assignment-footer span {
  color: var(--muted);
  font-size: 0.75rem;
}
@media (max-width: 680px) {
  .detail-header,
  .assignment-footer {
    display: grid;
  }
  .health-strip {
    grid-template-columns: 1fr;
  }
  .health-strip > div {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
  .health-strip > div:last-child {
    border-bottom: 0;
  }
}
</style>
