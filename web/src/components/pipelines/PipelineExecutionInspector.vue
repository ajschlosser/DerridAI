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
import { computed } from "vue";
import PipelineGraphDiagram from "./PipelineGraphDiagram.vue";
import PipelineRunTracePanel from "./PipelineRunTracePanel.vue";
import UiButton from "../ui/UiButton.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import { configurationForTrace } from "../../domain/pipelineGraph";
import {
  formatPipelineDate,
  pipelinePurposeLabel,
  pipelineRunStatusLabel,
} from "../../domain/pipelinePresentation";
import { pipelineRunTone } from "../../domain/pipelineStudioPresentation";
import {
  findTerm,
  purposeForFeature,
  purposeText,
  termLabel,
} from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelinePurpose,
  PipelineRunTrace,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  run: PipelineRunTrace;
  pipelines: PipelineDefinition[];
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  strategies: PipelineStrategy[];
}>();
const emit = defineEmits<{ openConfiguration: [key: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const configuration = computed(() => configurationForTrace(props.run, props.pipelines));
const workflow = computed(() => {
  const purpose = purposeForFeature(props.purposes, props.run.feature);
  const category = purpose ? findTerm(props.vocabulary.categories, purpose.category) : null;
  return {
    category: category
      ? termLabel(category, t)
      : t("pipelines.unregistered_purpose", "Unregistered purpose"),
    purpose: purpose
      ? purposeText(purpose, "label", t)
      : pipelinePurposeLabel(props.run.feature, t),
  };
});
const pipelineName = computed(
  () =>
    props.pipelines.find(
      (item) =>
        item.pipeline_id === props.run.pipeline_id && item.version === props.run.pipeline_version,
    )?.name || props.run.pipeline_id,
);
const duration = computed(() => {
  const value = props.run.total_elapsed_ms;
  if (value == null) return "—";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(value < 10000 ? 2 : 1)} s`;
});
</script>

<template>
  <article
    class="execution-inspector"
    :aria-label="t('pipelines.execution_details', 'Execution details')"
  >
    <header class="trace-summary">
      <p class="trace-workflow">
        <strong>{{ workflow.category }}</strong>
        <span aria-hidden="true">·</span>
        <span>{{ workflow.purpose }}</span>
      </p>
      <h3 class="trace-pipeline">
        {{ pipelineName }} <small>v{{ run.pipeline_version }}</small>
      </h3>
      <p class="trace-status">
        <UiStatusBadge
          :label="pipelineRunStatusLabel(run.status, t)"
          :tone="pipelineRunTone(run.status)"
        />
        <span>{{ formatPipelineDate(run.started_at, i18n.locale) }} · {{ duration }}</span>
      </p>
      <UiButton
        v-if="configuration.catalogKey"
        :label="t('pipelines.open_configuration', 'Open configuration')"
        @click="emit('openConfiguration', configuration.catalogKey)"
      />
    </header>

    <p class="trace-relate">
      {{
        configuration.catalogKey
          ? t(
              "pipelines.trace_vs_config",
              "The diagram overlays what ran on the saved stage graph. Stages that did not run stay visible.",
            )
          : t(
              "pipelines.configuration_missing",
              "This version is not in the current catalog. The diagram uses the configuration stored with the trace.",
            )
      }}
    </p>

    <PipelineGraphDiagram
      :stages="configuration.stages"
      :entry-stage-ids="configuration.entryStageIds"
      :strategies="strategies"
      :vocabulary="vocabulary"
      :execution="run"
      stack-inspector
      :title="t('pipelines.execution_diagram', 'Execution diagram')"
      :description="
        t(
          'pipelines.execution_diagram_help',
          'Filled nodes ran. Dim nodes are configured steps this run did not reach. A dashed outline is a step observed only in the trace.',
        )
      "
    />

    <details class="trace-audit">
      <summary>{{ t("pipelines.stage_details", "Stage details") }}</summary>
      <PipelineRunTracePanel :trace="run" hide-header />
    </details>

    <details class="trace-technical">
      <summary>{{ t("pipelines.technical_details", "Technical details") }}</summary>
      <dl>
        <div>
          <dt>{{ t("pipelines.feature_id", "Feature ID") }}</dt>
          <dd>
            <code>{{ run.feature }}</code>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.pipeline", "Pipeline") }}</dt>
          <dd>
            <code>{{ run.pipeline_id }}@{{ run.pipeline_version }}</code>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.resolved_hash", "Resolved hash") }}</dt>
          <dd>
            <code>{{ run.resolved_hash }}</code>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.run_id", "Run ID") }}</dt>
          <dd>
            <code>{{ run.run_id }}</code>
          </dd>
        </div>
        <div v-if="run.owner">
          <dt>{{ t("pipelines.owner", "Owner") }}</dt>
          <dd>{{ run.owner }}</dd>
        </div>
      </dl>
    </details>
  </article>
</template>

<style scoped>
.execution-inspector {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.trace-summary {
  display: grid;
  justify-items: start;
  gap: var(--space-2);
}
.trace-workflow {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.trace-workflow strong {
  font-weight: 800;
}
.trace-pipeline {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.25rem;
  line-height: var(--lh-tight);
}
.trace-pipeline small {
  color: var(--text-tertiary);
  font-size: 0.875rem;
}
.trace-status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.875rem;
}
.trace-relate {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.trace-audit,
.trace-technical {
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.trace-audit summary,
.trace-technical summary {
  width: fit-content;
  color: var(--text-primary);
  font-size: 0.9375rem;
  font-weight: var(--fw-bold);
  cursor: pointer;
}
.trace-audit summary:focus-visible,
.trace-technical summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.trace-audit > :not(summary) {
  margin-top: var(--space-3);
}
.trace-technical dl {
  display: grid;
  gap: var(--space-2);
  margin: var(--space-2) 0 0;
}
.trace-technical dl > div {
  display: grid;
  gap: 2px;
}
.trace-technical dt {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.trace-technical dd {
  margin: 0;
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
.trace-technical code {
  font-size: 0.75rem;
}
</style>
