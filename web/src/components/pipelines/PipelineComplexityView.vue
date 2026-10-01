<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import { findTerm, termDescription, termLabel } from "../../domain/pipelineWorkflows";
import { pipelineStrategyLabel } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAnalysis,
  PipelineLatencyEstimate,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  complexity: PipelineAnalysis["complexity"];
  latency: PipelineLatencyEstimate;
  strategies: PipelineStrategy[];
  vocabulary?: PipelineWorkflowVocabulary;
  selectedStageId?: string;
}>();
const emit = defineEmits<{ selectStage: [id: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const summary = computed(() => props.complexity.summary);
const observed = computed(
  () => new Map(props.latency.stages.map((row) => [row.stage_id, row.observed_scaling])),
);
const observedScope = computed(
  () => new Map(props.latency.stages.map((row) => [row.stage_id, row.observed_scope_scaling])),
);
const used = computed(() => {
  const ids = new Set(props.complexity.stages.flatMap((row) => row.variables));
  return (props.vocabulary?.complexity_variables ?? []).filter((term) => ids.has(term.id));
});

function term(list: "cost_drivers" | "complexity_orders", id: string) {
  const found = findTerm(props.vocabulary?.[list], id);
  return found ? termLabel(found, t) : id;
}
function strategyName(id: string) {
  const strategy = props.strategies.find((item) => item.strategy_id === id);
  return strategy ? pipelineStrategyLabel(strategy, t) : id;
}
function candidates(value: number | null, bounded: boolean) {
  return bounded && value != null
    ? `≤ ${value.toLocaleString(i18n.locale)}`
    : t("pipelines.complexity_request_bound", "set by the request");
}
const callRows = computed(() =>
  Object.entries(summary.value?.model_calls ?? {}).map(([driver, row]) => ({
    driver,
    label: term("cost_drivers", driver),
    count: row.calls_known
      ? String(row.max_calls)
      : t("pipelines.complexity_calls_unbounded", "depends on candidates"),
    stages: row.stage_ids.join(", "),
  })),
);
</script>

<template>
  <div v-if="summary" class="complexity">
    <ul class="findings">
      <li>
        <strong>{{ t("pipelines.complexity_dominant", "Costliest step") }}</strong>
        {{ summary.dominant_stage_id }} ·
        <code>{{ summary.dominant_time }}</code>
        — {{ term("complexity_orders", summary.dominant_order_id) }},
        {{ term("cost_drivers", summary.dominant_driver).toLowerCase() }}
      </li>
      <li v-if="summary.scales_with_scope">
        <strong>{{ t("pipelines.complexity_scales", "Grows with the collection") }}</strong>
        {{
          i18n.tf(
            "pipelines.complexity_scales_in",
            "Searching in {stages} reads or indexes the collection, so these stages slow down as the corpus grows.",
            { stages: summary.scope_stage_ids.join(", ") },
          )
        }}
      </li>
      <li v-else>
        <strong>{{ t("pipelines.complexity_flat", "Independent of collection size") }}</strong>
        {{
          t(
            "pipelines.complexity_flat_help",
            "No stage reads the whole collection; cost depends on the candidates and text each stage receives.",
          )
        }}
      </li>
      <li>
        <strong>{{ t("pipelines.complexity_bound", "Candidates after retrieval") }}</strong>
        {{ candidates(summary.candidate_bound, !summary.candidates_request_bound) }}
        <template v-if="summary.candidates_request_bound">
          —
          {{
            t(
              "pipelines.complexity_request_bound_help",
              "set a candidate limit on each retrieval stage to bound everything after it",
            )
          }}
        </template>
      </li>
      <li v-if="callRows.length">
        <strong>{{ t("pipelines.complexity_calls", "Model calls, worst case") }}</strong>
        <span v-for="(row, index) in callRows" :key="row.driver">
          <template v-if="index">; </template>{{ row.label }} × {{ row.count }}
          <small>({{ row.stages }})</small>
        </span>
      </li>
    </ul>

    <p class="formula">
      <span class="formula-label">{{
        t("pipelines.complexity_total", "Time, summed over stages")
      }}</span>
      <code>{{ summary.time_terms.join("  +  ") || "O(1)" }}</code>
    </p>

    <table class="stages">
      <caption class="visually-hidden">
        {{
          t("pipelines.complexity_table_caption", "Declared cost per stage")
        }}
      </caption>
      <thead>
        <tr>
          <th scope="col">{{ t("pipelines.stage", "Stage") }}</th>
          <th scope="col">{{ t("pipelines.complexity_time", "Time") }}</th>
          <th scope="col">{{ t("pipelines.complexity_space", "Space") }}</th>
          <th scope="col">{{ t("pipelines.complexity_sees", "Receives (n)") }}</th>
          <th scope="col">{{ t("pipelines.complexity_driver", "Mostly spent on") }}</th>
          <th scope="col">{{ t("pipelines.complexity_observed", "Measured growth") }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in complexity.stages"
          :key="row.stage_id"
          :data-selected="row.stage_id === selectedStageId"
        >
          <th scope="row">
            <button type="button" class="stage-link" @click="emit('selectStage', row.stage_id)">
              {{ row.stage_id }}
            </button>
            <small>{{ strategyName(row.strategy_id) }}</small>
            <UiStatusBadge
              v-if="row.conditional"
              :label="t('pipelines.complexity_fallback_only', 'Fallback only')"
              tone="neutral"
              :show-dot="false"
            />
          </th>
          <td>
            <code>{{ row.time }}</code>
            <UiStatusBadge
              v-if="row.scales_with_scope"
              :label="t('pipelines.complexity_scope_badge', 'Scans collection')"
              tone="warning"
              :show-dot="false"
            />
          </td>
          <td>
            <code>{{ row.space }}</code>
          </td>
          <td>{{ row.variables.includes("n") ? candidates(row.n_in, row.n_in_bounded) : "—" }}</td>
          <td>{{ term("cost_drivers", row.driver) }}</td>
          <td>
            <template v-if="observed.get(row.stage_id)">
              <code>n^{{ observed.get(row.stage_id)?.exponent }}</code>
              <small>
                R² {{ observed.get(row.stage_id)?.r_squared }} ·
                {{ observed.get(row.stage_id)?.points }}
                {{ t("pipelines.complexity_runs", "runs") }}
              </small>
            </template>
            <span v-else-if="!observedScope.get(row.stage_id)" class="none">—</span>
            <template v-if="observedScope.get(row.stage_id)">
              <code>N^{{ observedScope.get(row.stage_id)?.exponent }}</code>
              <small>
                R² {{ observedScope.get(row.stage_id)?.r_squared }} ·
                {{ observedScope.get(row.stage_id)?.points }}
                {{ t("pipelines.complexity_runs", "runs") }}
              </small>
            </template>
          </td>
        </tr>
      </tbody>
    </table>

    <details class="glossary">
      <summary>{{ t("pipelines.complexity_glossary", "What the letters mean") }}</summary>
      <dl>
        <template v-for="item in used" :key="item.id">
          <dt>
            <code>{{ item.label }}</code>
          </dt>
          <dd>{{ termDescription(item, t) }}</dd>
        </template>
      </dl>
      <p>
        {{
          t(
            "pipelines.complexity_declared_note",
            "These costs are declared for each strategy from its implementation, not measured. Measured growth compares elapsed time with the candidates a stage received, when enough runs exist.",
          )
        }}
      </p>
    </details>
  </div>
  <p v-else class="none">{{ t("pipelines.complexity_none", "Enable a stage to see its cost.") }}</p>
</template>

<style scoped>
.complexity {
  display: grid;
  gap: var(--space-3);
}
.findings {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.findings strong {
  display: block;
  color: var(--text-primary);
  font-size: 0.8125rem;
}
.findings small {
  color: var(--text-tertiary);
}
.formula {
  display: grid;
  gap: 2px;
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  overflow-x: auto;
}
.formula-label {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.formula code,
.stages code {
  color: var(--text-primary);
  font-size: 0.8125rem;
}
.stages {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}
.stages th,
.stages td {
  padding: var(--space-2);
  border-bottom: 1px solid var(--border-subtle);
  text-align: start;
  vertical-align: top;
}
.stages thead th {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.stages tbody th {
  display: grid;
  gap: 2px;
  font-weight: 600;
}
.stages small {
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
.glossary {
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
.glossary summary {
  cursor: pointer;
  color: var(--accent-fg);
  font-weight: 700;
}
.glossary dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-1) var(--space-3);
  margin: var(--space-2) 0;
}
.glossary dd {
  margin: 0;
}
.none {
  color: var(--text-tertiary);
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
