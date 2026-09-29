<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import PipelineGraphDiagram from "./PipelineGraphDiagram.vue";
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
        <span class="action-with-help">
          <button class="btn" type="button" :disabled="cloning" @click="emit('clone')">
            <AppIcon name="copy" />
            {{
              cloning
                ? t("pipelines.preparing_clone", "Preparing copy…")
                : t("pipelines.clone", "Clone & edit")
            }}
          </button>
          <UiTooltip
            :text="
              t(
                'pipelines.clone_help',
                'Built-in and saved pipeline versions are immutable. Clone & edit asks the server for a safe new draft version, leaving the original untouched. The new copy is not used by Research until you save it and explicitly make it active.',
              )
            "
          />
        </span>
        <span class="action-with-help">
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
          <UiTooltip
            :text="
              t(
                'pipelines.assign_help',
                'Making a version active changes the system-wide pipeline assignment for this feature. It does not rewrite previous runs: each run keeps the exact pipeline version it used.',
              )
            "
          />
        </span>
      </div>
    </header>

    <dl class="health-strip">
      <div>
        <dt class="label-with-help">
          {{ t("pipelines.graph_validation", "Graph validation") }}
          <UiTooltip
            :text="
              t(
                'pipelines.graph_validation_help',
                'Validation checks the structure of the recipe: stage IDs, connections, configuration types and ranges, and other rules that can be checked before execution.',
              )
            "
          />
        </dt>
        <dd>
          {{
            pipeline.validation?.valid === false
              ? t("pipelines.invalid", "Invalid")
              : t("pipelines.valid", "Valid")
          }}
        </dd>
      </div>
      <div>
        <dt class="label-with-help">
          {{ t("pipelines.runtime_support", "Runtime support") }}
          <UiTooltip
            :text="
              t(
                'pipelines.runtime_support_help',
                'A graph can be structurally valid but still not be executable by the current application adapter. “Executable” means DerridAI currently has runtime code that can carry out this exact graph shape.',
              )
            "
          />
        </dt>
        <dd>
          {{
            pipeline.runtime_support?.supported
              ? t("pipelines.executable", "Executable")
              : t("pipelines.inspect_only", "Inspect only")
          }}
        </dd>
      </div>
      <div>
        <dt class="label-with-help">
          {{ t("pipelines.assignment", "Assignment") }}
          <UiTooltip
            :text="
              t(
                'pipelines.assignment_help',
                'The assignment is the pipeline version DerridAI will use by default for this feature. Other saved versions remain available for history, inspection, and—where authorized—explicit per-run selection.',
              )
            "
          />
        </dt>
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
    <p
      v-if="
        pipeline.purpose === 'evidence_recovery' &&
        pipeline.runtime_support?.celf_compliant === false
      "
      class="support-note"
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

    <PipelineGraphDiagram
      :stages="pipeline.stages"
      :entry-stage-ids="pipeline.entry_stage_ids"
      :strategies="strategies"
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
      <PipelineStageList :pipeline="pipeline" :strategies="strategies" />
    </details>

    <footer v-if="assignment && assignment.source !== 'built_in'" class="assignment-footer">
      <div>
        <strong>{{ t("pipelines.custom_assignment", "Custom system assignment") }}</strong>
        <span>
          {{ assignment.feature }} · {{ assignment.pipeline_id }}@{{ assignment.pipeline_version }}
        </span>
      </div>
      <button class="btn" type="button" :disabled="assigning" @click="emit('resetAssignment')">
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
.action-with-help,
.label-with-help {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.reading-note {
  display: grid;
  gap: 3px;
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--soft);
  font-size: 0.77rem;
}
.reading-note span {
  color: var(--muted);
  line-height: 1.45;
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
.stage-details {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
}
.stage-details summary {
  padding: 10px 12px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 750;
}
.stage-details summary:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: -2px;
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
