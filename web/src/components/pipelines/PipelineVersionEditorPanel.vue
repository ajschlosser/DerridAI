<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import PipelineDefinitionEditor from "./PipelineDefinitionEditor.vue";
import UiButton from "../ui/UiButton.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import { pipelineDefinitionStatusLabel } from "../../domain/pipelinePresentation";
import { pipelineStatusTone } from "../../domain/pipelineStudioPresentation";
import { findTerm, purposeText, termLabel } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAnalysis,
  PipelineDefinition,
  PipelinePurpose,
  PipelineStrategy,
  PipelineStrategyLatency,
  PipelineValidationResponse,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";
const props = defineProps<{
  strategies: PipelineStrategy[];
  purpose: PipelinePurpose | null;
  vocabulary: PipelineWorkflowVocabulary;
  validation: PipelineValidationResponse | null;
  saving: boolean;
  /** Server analysis of the draft (wiring, cost, latency); omit to hide those panels. */
  analysis?: PipelineAnalysis | null;
  analysisLoading?: boolean;
  analysisError?: string;
  strategyLatency?: Record<string, PipelineStrategyLatency> | null;
}>();

const model = defineModel<PipelineDefinition>({ required: true });
const emit = defineEmits<{
  cancel: [];
  validate: [];
  save: [];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const category = computed(() =>
  props.purpose ? findTerm(props.vocabulary.categories, props.purpose.category) : null,
);
const purposeLabel = computed(() =>
  props.purpose ? purposeText(props.purpose, "label", t) : model.value.purpose,
);

// A result describes the draft that was validated; later edits make it stale.
const validatedSnapshot = ref(props.validation ? JSON.stringify(model.value) : "");
watch(
  () => props.validation,
  (next) => {
    validatedSnapshot.value = next ? JSON.stringify(model.value) : "";
  },
);
const stale = computed(
  () => Boolean(props.validation) && validatedSnapshot.value !== JSON.stringify(model.value),
);

const errorCount = computed(
  () => props.validation?.validation.issues.filter((issue) => issue.level === "error").length ?? 0,
);
const status = computed<{ label: string; tone: "neutral" | "success" | "warning" | "danger" }>(
  () => {
    const result = props.validation;
    if (!result)
      return { label: t("pipelines.validation_not_run", "Not validated"), tone: "neutral" };
    if (stale.value)
      return {
        label: t("pipelines.validation_stale", "Changed since last validation"),
        tone: "warning",
      };
    if (!result.validation.valid) {
      const count = Math.max(1, errorCount.value);
      return {
        label:
          count === 1
            ? t("pipelines.validation_one_change", "1 change required")
            : i18n.tf("pipelines.validation_changes", "{count} changes required", { count }),
        tone: "danger",
      };
    }
    return result.runtime_supported
      ? { label: t("pipelines.validation_executable", "Valid · Executable"), tone: "success" }
      : { label: t("pipelines.validation_inspect_only", "Valid · Inspect only"), tone: "warning" };
  },
);
const showIssues = computed(
  () =>
    Boolean(props.validation) &&
    !stale.value &&
    (props.validation!.validation.issues.length > 0 || !props.validation!.runtime_supported),
);
</script>

<template>
  <section class="editor-card" aria-labelledby="pipeline-editor-title">
    <header class="editor-heading">
      <div class="heading-main">
        <p class="detail-kicker">
          <span v-if="category">{{ termLabel(category, t) }}</span>
          <span v-if="category" aria-hidden="true"> · </span>
          <span>{{ purposeLabel }}</span>
        </p>
        <h3 id="pipeline-editor-title">
          {{
            model.derived_from
              ? t("pipelines.new_version", "New pipeline version")
              : t("pipelines.new_pipeline_heading", "New pipeline")
          }}
        </h3>
        <p class="editor-subtitle">
          {{ model.name || t("pipelines.unnamed_pipeline", "Unnamed pipeline") }} ·
          <code>{{ model.pipeline_id || "—" }}@{{ model.version }}</code>
        </p>
        <div class="heading-status">
          <UiStatusBadge
            :label="pipelineDefinitionStatusLabel(model.status, t)"
            :tone="pipelineStatusTone(model.status)"
          />
          <span role="status">
            <UiStatusBadge :label="status.label" :tone="status.tone" />
          </span>
          <span class="purpose-note">
            {{ t("pipelines.editor_purpose_fixed_short", "Purpose is fixed for this version.") }}
            <UiTooltip
              :text="
                i18n.tf(
                  'pipelines.editor_purpose_fixed',
                  'This new version remains a {purpose} pipeline. To create a pipeline for another workflow, begin from a pipeline for that workflow instead.',
                  { purpose: purposeLabel },
                )
              "
            />
          </span>
        </div>
      </div>
      <div
        class="editor-actions"
        role="group"
        :aria-label="t('pipelines.editor_actions', 'Editor actions')"
      >
        <span class="action-with-help">
          <UiButton
            :label="t('pipelines.validate', 'Validate')"
            :disabled="saving"
            @click="emit('validate')"
          />
          <UiTooltip
            :text="
              t(
                'pipelines.validate_help',
                'Validation is a dry check. It does not run the pipeline against your corpus and does not save anything. It checks graph structure, registered strategy settings, and current runtime support.',
              )
            "
          />
        </span>
        <span class="action-with-help">
          <UiButton
            variant="primary"
            icon="check"
            :label="
              saving
                ? t('pipelines.saving', 'Saving…')
                : t('pipelines.save_version', 'Save version')
            "
            :disabled="saving"
            @click="emit('save')"
          />
          <UiTooltip
            :text="
              t(
                'pipelines.save_version_help',
                'Saving creates a new immutable pipeline version for auditability. It does not replace the source version and does not make the new version the system default.',
              )
            "
          />
        </span>
        <UiButton :label="t('common.cancel', 'Cancel')" @click="emit('cancel')" />
      </div>
    </header>

    <p class="editor-help">
      {{
        t(
          "pipelines.configure_clone_help",
          "Edit the copy below. Validation checks whether the graph is internally coherent and whether the current runtime knows how to execute it. Saving does not activate it.",
        )
      }}
    </p>

    <PipelineDefinitionEditor
      v-model="model"
      :strategies="strategies"
      :purpose="purpose"
      :vocabulary="vocabulary"
      :analysis="analysis"
      :analysis-loading="analysisLoading"
      :analysis-error="analysisError"
      :strategy-latency="strategyLatency"
    />

    <div v-if="showIssues" class="validation-issues" :data-valid="validation!.validation.valid">
      <p v-if="!validation!.runtime_supported">
        {{
          validation!.runtime_error ||
          t(
            "pipelines.not_runtime_supported",
            "This graph is not executable by the current adapter.",
          )
        }}
      </p>
      <ul v-if="validation!.validation.issues.length">
        <li
          v-for="issue in validation!.validation.issues"
          :key="`${issue.code}:${issue.stage_id || ''}`"
          :data-level="issue.level"
        >
          <strong v-if="issue.stage_id">{{ issue.stage_id }}</strong>
          {{ issue.message }}
        </li>
      </ul>
    </div>

    <footer class="editor-command-bar">
      <span class="command-status">
        <UiStatusBadge :label="status.label" :tone="status.tone" />
      </span>
      <UiButton
        variant="primary"
        icon="check"
        :label="
          saving ? t('pipelines.saving', 'Saving…') : t('pipelines.save_version', 'Save version')
        "
        :disabled="saving"
        @click="emit('save')"
      />
    </footer>
  </section>
</template>

<style scoped>
.editor-card {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.editor-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.heading-main {
  min-width: 0;
}
.detail-kicker {
  margin: 0 0 var(--space-1);
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.editor-heading h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.375rem;
  line-height: var(--lh-tight);
}
.editor-subtitle {
  margin: var(--space-1) 0 0;
  color: var(--text-tertiary);
  font-size: 0.875rem;
}
.heading-status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
.purpose-note {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.editor-help {
  max-width: var(--measure);
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.editor-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.action-with-help {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.validation-issues {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--tone-warn-edge);
  border-radius: var(--radius-control);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.875rem;
}
.validation-issues[data-valid="false"] {
  border-color: var(--tone-danger-edge);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.validation-issues p {
  margin: 0;
}
.validation-issues ul {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding-left: var(--space-4);
}
.editor-command-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
@media (max-width: 680px) {
  .editor-actions {
    width: 100%;
  }
}
</style>
