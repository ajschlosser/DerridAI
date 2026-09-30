<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import UiButton from "../ui/UiButton.vue";
import UiMenu, { type UiMenuItem } from "../ui/UiMenu.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import { pipelineDefinitionStatusLabel } from "../../domain/pipelinePresentation";
import {
  pipelineAssignmentTone,
  pipelineRuntimeTone,
  pipelineStatusTone,
  pipelineValidationTone,
} from "../../domain/pipelineStudioPresentation";
import { findTerm, purposeLabelFor, termLabel } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAssignment,
  PipelineDefinition,
  PipelinePurpose,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  pipeline: PipelineDefinition;
  purpose: PipelinePurpose | null;
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  /** The assignment currently in force for this pipeline's feature, if any. */
  assignment?: PipelineAssignment | null;
  assigned: boolean;
  canAssign: boolean;
  assigning: boolean;
  cloning: boolean;
}>();
const emit = defineEmits<{ clone: []; assign: []; resetAssignment: [] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const category = computed(() =>
  props.purpose ? findTerm(props.vocabulary.categories, props.purpose.category) : null,
);
const assignDisabledReason = computed(() => {
  if (props.assigning || props.canAssign) return "";
  if (!props.purpose)
    return t(
      "pipelines.assign_reason_unregistered",
      "This pipeline’s purpose is not a registered workflow, so it cannot be assigned.",
    );
  if (props.pipeline.status !== "active")
    return t("pipelines.assign_reason_inactive", "Only active pipeline versions can be assigned.");
  return (
    props.pipeline.runtime_support?.reason ||
    t(
      "pipelines.assign_reason_unsupported",
      "This pipeline cannot be assigned because the current adapter cannot execute it.",
    )
  );
});
const assignmentHelp = computed(() => {
  const current = props.assignment;
  if (props.assigned)
    return t("pipelines.contract_assigned", "Assigned — DerridAI runs this version");
  if (!current) return t("pipelines.not_assigned", "Not assigned");
  return i18n.tf("pipelines.contract_other_assigned", "Not assigned — {pipeline} runs instead", {
    pipeline: `${current.pipeline_id}@${current.pipeline_version}`,
  });
});
const moreItems = computed<UiMenuItem[]>(() =>
  props.assignment && props.assignment.source !== "built_in"
    ? [
        {
          id: "reset",
          label: t("pipelines.restore_default", "Restore built-in default"),
          reason: props.assigning
            ? t("pipelines.assignment_busy", "An assignment change is in progress.")
            : undefined,
        },
      ]
    : [],
);
</script>

<template>
  <header class="definition-header">
    <div class="header-main">
      <p class="header-kicker">
        <span v-if="category">{{ termLabel(category, t) }}</span>
        <span v-if="category" aria-hidden="true"> · </span>
        <span>{{ purposeLabelFor(purposes, pipeline.purpose, t) }}</span>
      </p>
      <h3>{{ pipeline.name }}</h3>
      <p class="header-version">v{{ pipeline.version }}</p>
    </div>

    <div class="detail-actions">
      <span v-if="!assigned" class="action-with-help">
        <UiButton
          variant="primary"
          icon="check"
          :label="t('pipelines.assign', 'Make active')"
          :disabled="!canAssign || assigning"
          :disabled-reason="assignDisabledReason"
          @click="emit('assign')"
        />
        <UiTooltip
          :text="
            t(
              'pipelines.assign_help',
              'Making a version active changes the system-wide pipeline assignment for this feature. It does not rewrite previous runs: each run keeps the exact pipeline version it used.',
            )
          "
        />
      </span>
      <span class="action-with-help">
        <UiButton
          icon="copy"
          :label="
            cloning
              ? t('pipelines.preparing_clone', 'Preparing copy…')
              : t('pipelines.clone', 'Clone & edit')
          "
          :disabled="cloning"
          @click="emit('clone')"
        />
        <UiTooltip
          :text="
            t(
              'pipelines.clone_help_purpose',
              'Built-in and saved pipeline versions are immutable. Clone & edit asks the server for a safe new draft version, leaving the original untouched. The copy keeps this pipeline’s purpose, and DerridAI does not use it until you save it and explicitly make it active.',
            )
          "
        />
      </span>
      <UiMenu
        v-if="moreItems.length"
        :label="t('pipelines.more_actions', 'More')"
        :items="moreItems"
        align="end"
        @select="emit('resetAssignment')"
      />
    </div>

    <div class="header-status" role="group" :aria-label="t('pipelines.status', 'Status')">
      <UiStatusBadge
        v-if="pipeline.status !== 'active'"
        :label="pipelineDefinitionStatusLabel(pipeline.status, t)"
        :tone="pipelineStatusTone(pipeline.status)"
      />
      <UiStatusBadge
        :label="
          assigned
            ? t('pipelines.active_assignment', 'Active assignment')
            : t('pipelines.not_assigned', 'Not assigned')
        "
        :tone="pipelineAssignmentTone(assigned)"
        :help="assignmentHelp"
      />
      <UiStatusBadge
        :label="
          pipeline.runtime_support?.supported
            ? t('pipelines.executable', 'Executable')
            : t('pipelines.inspect_only', 'Inspect only')
        "
        :tone="pipelineRuntimeTone(pipeline)"
        :help="
          t(
            'pipelines.runtime_support_help',
            'A graph can be structurally valid but still not be executable by the current application adapter. “Executable” means DerridAI currently has runtime code that can carry out this exact graph shape.',
          )
        "
      />
      <UiStatusBadge
        :label="
          pipeline.validation?.valid === false
            ? t('pipelines.invalid', 'Invalid')
            : t('pipelines.valid', 'Valid')
        "
        :tone="pipelineValidationTone(pipeline)"
        :help="
          t(
            'pipelines.graph_validation_help',
            'Validation checks the structure of the recipe: stage IDs, connections, configuration types and ranges, and other rules that can be checked before execution.',
          )
        "
      />
    </div>

    <details class="header-technical">
      <summary>{{ t("pipelines.technical_details", "Technical details") }}</summary>
      <dl>
        <div>
          <dt>{{ t("pipelines.pipeline_id", "Pipeline ID") }}</dt>
          <dd>
            <code>{{ pipeline.pipeline_id }}@{{ pipeline.version }}</code>
          </dd>
        </div>
        <div v-if="pipeline.derived_from">
          <dt>{{ t("pipelines.derived_from", "derived from") }}</dt>
          <dd>
            <code>{{ pipeline.derived_from }}</code>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.built_in", "Built in") }}</dt>
          <dd>{{ pipeline.built_in ? t("common.yes", "Yes") : t("common.no", "No") }}</dd>
        </div>
        <div v-if="assignment">
          <dt>{{ t("pipelines.custom_assignment", "Custom system assignment") }}</dt>
          <dd>
            <code>
              {{ assignment.feature }} · {{ assignment.pipeline_id }}@{{
                assignment.pipeline_version
              }}
            </code>
          </dd>
        </div>
      </dl>
    </details>
  </header>
</template>

<style scoped>
.definition-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-2) var(--space-4);
  align-items: start;
}
.header-main {
  min-width: 0;
}
.header-kicker {
  margin: 0 0 var(--space-1);
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.definition-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.375rem;
  line-height: var(--lh-tight);
  overflow-wrap: anywhere;
}
.header-version {
  margin: var(--space-1) 0 0;
  color: var(--text-tertiary);
  font-size: 0.875rem;
  font-weight: var(--fw-bold);
}
.detail-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}
.action-with-help {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.header-status,
.header-technical {
  grid-column: 1 / -1;
}
.header-status {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.header-technical summary {
  width: fit-content;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  cursor: pointer;
}
.header-technical summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.header-technical dl {
  display: grid;
  gap: var(--space-2);
  margin: var(--space-2) 0 0;
}
.header-technical dl > div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.header-technical dt {
  min-width: 140px;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.header-technical dd {
  margin: 0;
  font-size: 0.8125rem;
}
.header-technical code {
  font-size: 0.75rem;
}
@media (max-width: 680px) {
  .definition-header {
    grid-template-columns: 1fr;
  }
  .detail-actions {
    justify-content: flex-start;
  }
}
</style>
