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
import UiButton from "../ui/UiButton.vue";
import UiMenu, { type UiMenuItem } from "../ui/UiMenu.vue";
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
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  runs: PipelineRunTrace[];
  pipelines: PipelineDefinition[];
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  selectedRunId: string;
  total: number;
  limit: number;
  offset: number;
}>();
const emit = defineEmits<{
  select: [runId: string];
  page: [offset: number];
  deleteRun: [runId: string];
  openConfiguration: [key: string];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

// Human workflow first; the raw feature ID stays in the inspector's technical details.
function runWorkflow(run: PipelineRunTrace) {
  const purpose = purposeForFeature(props.purposes, run.feature);
  const category = purpose ? findTerm(props.vocabulary.categories, purpose.category) : null;
  return {
    category: category
      ? termLabel(category, t)
      : t("pipelines.unregistered_purpose", "Unregistered purpose"),
    purpose: purpose ? purposeText(purpose, "label", t) : pipelinePurposeLabel(run.feature, t),
  };
}
function pipelineName(run: PipelineRunTrace) {
  return (
    props.pipelines.find(
      (item) => item.pipeline_id === run.pipeline_id && item.version === run.pipeline_version,
    )?.name || run.pipeline_id
  );
}
function duration(value?: number | null) {
  if (value == null) return "—";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(value < 10000 ? 2 : 1)} s`;
}
function menuItems(run: PipelineRunTrace): UiMenuItem[] {
  const key = configurationForTrace(run, props.pipelines).catalogKey;
  return [
    {
      id: "open",
      label: t("pipelines.open_configuration", "Open configuration"),
      reason: key
        ? undefined
        : t("pipelines.configuration_missing_short", "This version is not in the current catalog."),
    },
    { id: "delete", label: t("pipelines.delete_execution", "Delete execution") },
  ];
}
function onMenu(run: PipelineRunTrace, id: string) {
  if (id === "delete") emit("deleteRun", run.run_id);
  else {
    const key = configurationForTrace(run, props.pipelines).catalogKey;
    if (key) emit("openConfiguration", key);
  }
}
</script>

<template>
  <div class="execution-list">
    <div class="execution-list-scroll">
      <table class="run-table">
        <caption class="sr-only">
          {{
            t("pipelines.executions_title", "Execution history")
          }}
        </caption>
        <thead>
          <tr>
            <th scope="col">{{ t("pipelines.started", "Started") }}</th>
            <th scope="col">{{ t("pipelines.used_for", "Used for") }}</th>
            <th scope="col">{{ t("pipelines.pipeline", "Pipeline") }}</th>
            <th scope="col">{{ t("pipelines.status", "Status") }}</th>
            <th scope="col">{{ t("pipelines.duration", "Duration") }}</th>
            <th scope="col">
              <span class="sr-only">{{ t("pipelines.run_actions", "Actions") }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="run in runs"
            :key="run.run_id"
            :data-run="run.run_id"
            :class="{ selected: selectedRunId === run.run_id }"
            @click="emit('select', run.run_id)"
          >
            <th scope="row">
              <button
                type="button"
                class="row-select"
                :aria-current="selectedRunId === run.run_id ? 'true' : undefined"
                @click.stop="emit('select', run.run_id)"
              >
                {{ formatPipelineDate(run.started_at, i18n.locale) }}
              </button>
            </th>
            <td class="run-workflow">
              <strong>{{ runWorkflow(run).category }}</strong>
              <span>{{ runWorkflow(run).purpose }}</span>
            </td>
            <td class="run-pipeline">
              <span>{{ pipelineName(run) }}</span>
              <small>v{{ run.pipeline_version }}</small>
            </td>
            <td>
              <UiStatusBadge
                :label="pipelineRunStatusLabel(run.status, t)"
                :tone="pipelineRunTone(run.status)"
              />
            </td>
            <td class="numeric">{{ duration(run.total_elapsed_ms) }}</td>
            <td class="run-actions" @click.stop>
              <UiMenu
                label="⋯"
                :aria-label="
                  i18n.tf('pipelines.run_actions_for', 'Actions for run {run}', { run: run.run_id })
                "
                :items="menuItems(run)"
                :caret="false"
                align="end"
                @select="onMenu(run, $event)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="pager">
      <UiButton
        :label="t('common.previous', 'Previous')"
        :disabled="offset <= 0"
        @click="emit('page', Math.max(0, offset - limit))"
      />
      <UiButton
        :label="t('common.next', 'Next')"
        :disabled="offset + runs.length >= total"
        @click="emit('page', offset + limit)"
      />
    </div>
  </div>
</template>

<style scoped>
.execution-list {
  position: sticky;
  top: var(--pipeline-studio-sticky-top, var(--space-3));
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}
.execution-list-scroll {
  max-height: var(--pipeline-studio-pane-max-height, min(76dvh, 960px));
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.run-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
.run-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-strong);
  background: var(--surface-card);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
  text-align: left;
  white-space: nowrap;
}
.run-table td,
.run-table tbody th {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  text-align: left;
  vertical-align: middle;
}
.run-table tbody tr {
  cursor: pointer;
}
.run-table tbody tr:hover,
.run-table tbody tr.selected {
  background: var(--surface-selected);
}
.run-workflow,
.run-pipeline {
  display: grid;
  gap: 1px;
}
.run-workflow strong,
.run-pipeline span {
  color: var(--text-primary);
  font-size: 0.875rem;
}
.run-workflow span,
.run-pipeline small {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.numeric {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.row-select {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.row-select:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.run-actions :deep(.ui-menu-trigger) {
  min-height: var(--control-height-small);
  border-color: transparent;
  background: transparent;
}
.pager {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
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

@media (max-width: 1100px) {
  .execution-list {
    position: static;
  }
}
</style>
