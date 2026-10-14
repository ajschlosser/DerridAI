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
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import {
  formatMs,
  latencyBasisLabel,
  sampleLabel,
} from "../../domain/pipelineAnalysisPresentation";
import { pipelineStrategyLabel } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineLatencyEstimate,
  PipelineStageLatency,
  PipelineStrategy,
} from "../../types/pipelines";

const props = defineProps<{
  latency: PipelineLatencyEstimate;
  strategies: PipelineStrategy[];
  sample: { runs: number; pipeline_runs: number; exact_runs: number };
  selectedStageId?: string;
}>();
const emit = defineEmits<{ selectStage: [id: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const scaleMax = computed(() =>
  Math.max(1, ...props.latency.stages.map((row) => row.p90_ms ?? row.p50_ms ?? 0)),
);
const onCriticalPath = computed(() => new Set(props.latency.critical_path));
const missing = computed(
  () => props.latency.stages.filter((row) => !row.conditional && row.samples === 0).length,
);
const borrowed = computed(
  () => props.latency.stages.filter((row) => row.basis === "strategy").length,
);
const parallelGain = computed(() => {
  const typical = props.latency.typical_ms ?? 0;
  const path = props.latency.critical_path_ms ?? 0;
  return typical > 0 && path > 0 && typical - path > typical * 0.1;
});

function label(row: PipelineStageLatency) {
  const strategy = props.strategies.find((item) => item.strategy_id === row.strategy_id);
  return strategy ? pipelineStrategyLabel(strategy, t) : row.strategy_id;
}
function barStyle(row: PipelineStageLatency) {
  const p50 = ((row.p50_ms ?? 0) / scaleMax.value) * 100;
  const p90 = ((row.p90_ms ?? row.p50_ms ?? 0) / scaleMax.value) * 100;
  return { "--p50": `${p50}%`, "--p90": `${p90}%` };
}
function modelLine(row: PipelineStageLatency) {
  return row.by_model
    .filter((item) => item.samples > 0)
    .map(
      (item) =>
        `${item.model || item.provider || "?"}: ${formatMs(item.p50_ms, t)} (n=${item.samples})`,
    )
    .join(" · ");
}
</script>

<template>
  <div class="latency">
    <dl class="tiles">
      <div class="tile">
        <dt>
          {{ t("pipelines.latency_typical", "Typical") }}
          <UiTooltip
            :text="
              t(
                'pipelines.latency_typical_help',
                'The sum of each stage’s median time, counting a fallback stage only as often as it was reached. This is the time if stages run one after another.',
              )
            "
          />
        </dt>
        <dd>{{ formatMs(latency.typical_ms, t) }}</dd>
      </div>
      <div class="tile">
        <dt>
          {{ t("pipelines.latency_slow", "Slow day") }}
          <UiTooltip
            :text="
              t(
                'pipelines.latency_slow_help',
                'The sum of each stage’s 90th-percentile time. Stages are rarely all slow at once, so real runs are almost always faster than this.',
              )
            "
          />
        </dt>
        <dd>{{ formatMs(latency.slow_ms, t) }}</dd>
      </div>
      <div class="tile">
        <dt>
          {{ t("pipelines.latency_critical", "Longest chain") }}
          <UiTooltip
            :text="
              t(
                'pipelines.latency_critical_help',
                'The slowest unbroken path through the graph. If parallel branches run at the same time, this is the lower bound for the whole pipeline.',
              )
            "
          />
        </dt>
        <dd>{{ formatMs(latency.critical_path_ms, t) }}</dd>
      </div>
      <div class="tile">
        <dt>
          {{ t("pipelines.latency_observed", "Measured whole runs") }}
          <UiTooltip
            :text="
              t(
                'pipelines.latency_observed_help',
                'Actual end-to-end times of completed runs of this exact pipeline. Unlike the estimates, these include everything the pipeline did.',
              )
            "
          />
        </dt>
        <dd v-if="latency.observed_runs.samples">
          {{ formatMs(latency.observed_runs.p50_ms, t) }}
          <small>
            {{
              i18n.tf("pipelines.latency_p90_of", "p90 {time}", {
                time: formatMs(latency.observed_runs.p90_ms, t),
              })
            }}
            · {{ sampleLabel(latency.observed_runs, t) }}
          </small>
        </dd>
        <dd v-else class="none">
          {{ t("pipelines.latency_never_run", "Never run in this form") }}
        </dd>
      </div>
    </dl>

    <p v-if="!latency.stages.length" class="note" role="status">
      {{ t("pipelines.latency_no_stages", "Enable a stage to estimate latency.") }}
    </p>
    <p
      v-else-if="missing || borrowed || !latency.reliable"
      class="note"
      data-tone="warn"
      role="status"
    >
      <template v-if="missing">
        {{
          i18n.tf(
            "pipelines.latency_missing",
            "{count} stages have no recorded runs, so their time is not counted and the totals are lower bounds.",
            { count: missing },
          )
        }}
      </template>
      <template v-if="borrowed">
        {{
          i18n.tf(
            "pipelines.latency_borrowed",
            "{count} stages use figures from the same strategy in other pipelines.",
            { count: borrowed },
          )
        }}
      </template>
      {{
        t(
          "pipelines.latency_rough",
          "Treat these estimates as a rough guide until this pipeline has run more.",
        )
      }}
    </p>
    <p v-if="parallelGain" class="note">
      {{
        t(
          "pipelines.latency_parallel_hint",
          "The longest chain is shorter than the sum, so this pipeline has branches that could overlap if they run in parallel.",
        )
      }}
    </p>

    <table v-if="latency.stages.length" class="waterfall">
      <caption class="visually-hidden">
        {{
          t("pipelines.latency_table_caption", "Estimated latency per stage")
        }}
      </caption>
      <thead>
        <tr>
          <th scope="col">{{ t("pipelines.stage", "Stage") }}</th>
          <th scope="col">{{ t("pipelines.latency_median_p90", "Median (p90)") }}</th>
          <th scope="col" class="bar-col">{{ t("pipelines.latency_bar", "Time") }}</th>
          <th scope="col">{{ t("pipelines.latency_source", "Based on") }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in latency.stages"
          :key="row.stage_id"
          :data-selected="row.stage_id === selectedStageId"
          :data-critical="onCriticalPath.has(row.stage_id)"
        >
          <th scope="row">
            <button type="button" class="stage-link" @click="emit('selectStage', row.stage_id)">
              {{ row.stage_id }}
            </button>
            <small>{{ label(row) }}</small>
            <UiStatusBadge
              v-if="row.conditional"
              :label="
                i18n.tf('pipelines.latency_fallback_only', 'Fallback only · reached {share}', {
                  share: `${Math.round(row.reach * 100)}%`,
                })
              "
              tone="neutral"
              :show-dot="false"
            />
          </th>
          <td class="figure">
            <template v-if="row.samples">
              <strong>{{ formatMs(row.p50_ms, t) }}</strong>
              <small>({{ formatMs(row.p90_ms, t) }})</small>
              <small v-if="row.median_ms_per_input" class="per-item">
                {{
                  i18n.tf("pipelines.latency_per_item", "≈ {time} per candidate", {
                    time: formatMs(row.median_ms_per_input, t),
                  })
                }}
              </small>
            </template>
            <span v-else class="none">{{ t("pipelines.latency_unknown", "Unknown") }}</span>
          </td>
          <td class="bar-col">
            <span v-if="row.samples" class="bar" :style="barStyle(row)" aria-hidden="true">
              <span class="bar-slow"></span>
              <span class="bar-typical"></span>
            </span>
          </td>
          <td class="basis">
            <span>{{ latencyBasisLabel(row.basis, t) }}</span>
            <small>{{ sampleLabel(row, t) }}</small>
            <small v-if="modelLine(row)" class="models">{{ modelLine(row) }}</small>
          </td>
        </tr>
      </tbody>
    </table>

    <p class="foot">
      {{
        i18n.tf(
          "pipelines.latency_foot",
          "From {runs} recent runs across all pipelines and {own} runs of this pipeline in any version. Latency is operational measurement only; it says nothing about whether results are right.",
          { runs: sample.runs, own: sample.pipeline_runs },
        )
      }}
    </p>
  </div>
</template>

<style scoped>
.latency {
  display: grid;
  gap: var(--space-3);
}
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: var(--space-2);
  margin: 0;
}
.tile {
  display: grid;
  gap: 2px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.tile dt {
  display: flex;
  align-items: center;
  gap: 2px;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.tile dd {
  display: grid;
  margin: 0;
  color: var(--text-primary);
  font-size: 1.25rem;
  font-weight: 800;
}
.tile dd small {
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 600;
}
.none {
  color: var(--text-tertiary);
  font-size: 0.875rem;
  font-weight: 600;
}
.note {
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.note[data-tone="warn"] {
  border-color: var(--tone-warn-edge);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.waterfall {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}
.waterfall th,
.waterfall td {
  padding: var(--space-2);
  border-bottom: 1px solid var(--border-subtle);
  text-align: start;
  vertical-align: top;
}
.waterfall thead th {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.waterfall tbody th {
  display: grid;
  gap: 2px;
  font-weight: 600;
}
.waterfall tbody th small,
.figure small,
.basis small {
  display: block;
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 500;
}
tr[data-selected="true"] {
  background: var(--surface-selected);
}
.stage-link {
  justify-self: start;
  padding: 0;
  border: 0;
  background: none;
  color: var(--accent-fg);
  font: inherit;
  font-weight: 800;
  text-align: start;
  cursor: pointer;
}
.stage-link:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring, var(--accent));
  outline-offset: var(--focus-ring-offset);
}
.figure strong {
  color: var(--text-primary);
}
.bar-col {
  width: 34%;
  min-width: 120px;
}
.bar {
  position: relative;
  display: block;
  height: 14px;
  margin-top: 4px;
  border-radius: var(--radius-xs);
  background: var(--surface-inset);
}
.bar-slow,
.bar-typical {
  position: absolute;
  inset-block: 0;
  inset-inline-start: 0;
  border-radius: var(--radius-xs);
}
.bar-slow {
  width: var(--p90);
  background: var(--tone-info-edge);
  opacity: 0.45;
}
.bar-typical {
  width: var(--p50);
  background: var(--accent);
}
tr[data-critical="true"] .bar-typical {
  background: var(--viz-cat-2);
}
.foot {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  line-height: var(--lh-normal);
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
