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
import PipelineTypeChip from "./PipelineTypeChip.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import { formatMs, sampleLabel } from "../../domain/pipelineAnalysisPresentation";
import {
  pipelineCapabilityLabel,
  pipelineComputationLabel,
  pipelineDataTypeLabel,
  pipelineKey,
  pipelineStageFamilyHelp,
  pipelineStageFamilyLabel,
  pipelineStrategyDescription,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import {
  findTerm,
  purposeLabelFor,
  strategyComputation,
  termDescription,
  termLabel,
  type StrategyUsage,
} from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelinePurpose,
  PipelineStrategy,
  PipelineStrategyLatency,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  strategy: PipelineStrategy;
  usage: StrategyUsage;
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  /** Observed latency for this strategy, when recent runs exist. */
  latency?: PipelineStrategyLatency | null;
}>();
const emit = defineEmits<{ openPipeline: [key: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const effect = computed(() =>
  findTerm(props.vocabulary.scholarly_effects, props.strategy.scholarly_effect),
);
const note = computed(() => findTerm(props.vocabulary.effect_notes, props.strategy.effect_note));
const categories = computed(() =>
  props.usage.categories
    .map((id) => findTerm(props.vocabulary.categories, id))
    .filter((term) => term !== null),
);
function term(list: "cost_drivers" | "complexity_orders", id: string) {
  const found = findTerm(props.vocabulary[list], id);
  return found ? termLabel(found, t) : id;
}
const ORDER_IDS = [
  "constant",
  "sublinear",
  "linear_in_candidates",
  "linearithmic",
  "linear_in_scope",
  "superlinear",
  "model_inference",
  "generation",
];
function complexityOrderId(order: number) {
  return ORDER_IDS[order] ?? "constant";
}
const configKeys = computed(() => {
  const properties = (props.strategy.config_schema as { properties?: Record<string, unknown> })
    .properties;
  return Object.keys(properties || {});
});
</script>

<template>
  <aside
    class="strategy-inspector"
    :data-strategy="strategy.strategy_id"
    :aria-label="t('pipelines.strategy_details', 'Strategy details')"
  >
    <header>
      <h3>{{ pipelineStrategyLabel(strategy, t) }}</h3>
      <code>{{ strategy.strategy_id }}</code>
    </header>

    <section aria-labelledby="strategy-overview-title">
      <h4 id="strategy-overview-title">{{ t("pipelines.strategy_overview", "Overview") }}</h4>
      <p class="description">{{ pipelineStrategyDescription(strategy, t) }}</p>
      <dl>
        <div>
          <dt>{{ t("pipelines.strategy_family", "Family") }}</dt>
          <dd class="with-help">
            {{ pipelineStageFamilyLabel(strategy.family, t) }}
            <UiTooltip
              :text="pipelineStageFamilyHelp(strategy.family, t)"
              :label="t('pipelines.explain_stage_family', 'Explain this kind of stage')"
            />
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.strategy_input_output", "Input → output") }}</dt>
          <dd>
            {{ pipelineDataTypeLabel(strategy.input_type, t) }}
            <span aria-hidden="true">→</span>
            <span class="sr-only">{{ t("pipelines.to", "to") }}</span>
            {{ pipelineDataTypeLabel(strategy.output_type, t) }}
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.strategy_computation", "Computation") }}</dt>
          <dd>{{ pipelineComputationLabel(strategyComputation(strategy), t) }}</dd>
        </div>
        <div>
          <dt>{{ t("pipelines.strategy_requires", "Requires") }}</dt>
          <dd>
            {{
              strategy.capabilities.length
                ? strategy.capabilities.map((item) => pipelineCapabilityLabel(item, t)).join(", ")
                : t("pipelines.strategy_requires_nothing", "No external model or service")
            }}
          </dd>
        </div>
        <div v-if="effect" class="effect">
          <dt>{{ t("pipelines.scholarly_effect", "Scholarly effect") }}</dt>
          <dd class="with-help">
            <strong v-if="note">{{ termLabel(note, t) }}</strong>
            <span v-else>{{ termLabel(effect, t) }}</span>
            <UiTooltip
              :text="termDescription(effect, t)"
              :label="t('pipelines.explain_scholarly_effect', 'Explain this scholarly effect')"
            />
          </dd>
        </div>
      </dl>
    </section>

    <section aria-labelledby="strategy-contract-title">
      <h4 id="strategy-contract-title">
        {{ t("pipelines.strategy_contract", "Inputs, outputs and cost") }}
      </h4>
      <dl>
        <div>
          <dt>{{ t("pipelines.ports_inputs", "Inputs") }}</dt>
          <dd class="port-rows">
            <span v-for="port in strategy.inputs || []" :key="port.name" class="port-row">
              <code>{{ port.name }}</code>
              <PipelineTypeChip :type="port.data_type" />
              <small>
                {{
                  port.required
                    ? t("pipelines.ports_required", "Required")
                    : t("pipelines.ports_optional", "Optional")
                }}
                <template v-if="port.multiple">
                  · {{ t("pipelines.ports_merges", "merges several sources") }}
                </template>
              </small>
            </span>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.ports_outputs", "Outputs") }}</dt>
          <dd class="port-rows">
            <span v-for="port in strategy.outputs || []" :key="port.name" class="port-row">
              <code>{{ port.name }}</code>
              <PipelineTypeChip :type="port.data_type" />
            </span>
          </dd>
        </div>
        <template v-if="strategy.complexity">
          <div>
            <dt>{{ t("pipelines.complexity_time", "Time") }}</dt>
            <dd>
              <code>{{ strategy.complexity.time }}</code>
              · {{ term("complexity_orders", complexityOrderId(strategy.complexity.order)) }}
            </dd>
          </div>
          <div>
            <dt>{{ t("pipelines.complexity_space", "Space") }}</dt>
            <dd>
              <code>{{ strategy.complexity.space }}</code>
            </dd>
          </div>
          <div>
            <dt>{{ t("pipelines.complexity_driver", "Mostly spent on") }}</dt>
            <dd>{{ term("cost_drivers", strategy.complexity.driver) }}</dd>
          </div>
        </template>
        <div>
          <dt>{{ t("pipelines.strategy_observed_latency", "Observed latency") }}</dt>
          <dd v-if="latency && latency.samples">
            {{ formatMs(latency.p50_ms, t) }}
            <small> p90 {{ formatMs(latency.p90_ms, t) }} · {{ sampleLabel(latency, t) }} </small>
            <small v-if="latency.median_ms_per_input" class="block">
              {{
                i18n.tf("pipelines.latency_per_item", "≈ {time} per candidate", {
                  time: formatMs(latency.median_ms_per_input, t),
                })
              }}
            </small>
            <small v-if="latency.observed_scaling" class="block">
              {{
                i18n.tf(
                  "pipelines.strategy_observed_scaling",
                  "Elapsed time grows roughly as n^{exponent} (R² {r2}, {points} runs)",
                  {
                    exponent: latency.observed_scaling.exponent,
                    r2: latency.observed_scaling.r_squared,
                    points: latency.observed_scaling.points,
                  },
                )
              }}
            </small>
            <small v-if="latency.observed_scope_scaling" class="block">
              {{
                i18n.tf(
                  "pipelines.strategy_observed_scope_scaling",
                  "Elapsed time grows roughly as N^{exponent} with collection size (R² {r2}, {points} runs)",
                  {
                    exponent: latency.observed_scope_scaling.exponent,
                    r2: latency.observed_scope_scaling.r_squared,
                    points: latency.observed_scope_scaling.points,
                  },
                )
              }}
            </small>
            <small
              v-for="row in latency.by_model"
              :key="`${row.provider}:${row.model}`"
              class="block"
            >
              {{ row.model || row.provider || "?" }}: {{ formatMs(row.p50_ms, t) }} ({{
                sampleLabel(row, t)
              }})
            </small>
          </dd>
          <dd v-else class="empty">
            {{ t("pipelines.strategy_no_latency", "No recorded runs yet") }}
          </dd>
        </div>
      </dl>
    </section>

    <section aria-labelledby="strategy-used-by-title">
      <h4 id="strategy-used-by-title">{{ t("pipelines.strategy_used_by", "Used by") }}</h4>
      <p v-if="categories.length" class="workflows">
        {{ categories.map((term) => termLabel(term, t)).join(", ") }}
      </p>
      <p v-if="!usage.pipelines.length" class="empty">
        {{ t("pipelines.strategy_unused", "No current pipeline") }}
      </p>
      <ul v-else class="usage-list">
        <li v-for="pipeline in usage.pipelines" :key="pipelineKey(pipeline)">
          <button
            type="button"
            class="link-button"
            @click="emit('openPipeline', pipelineKey(pipeline))"
          >
            {{ pipeline.name }}
          </button>
          <span class="usage-meta">
            {{ purposeLabelFor(purposes, pipeline.purpose, t) }} · v{{ pipeline.version }}
          </span>
        </li>
      </ul>
    </section>

    <details class="strategy-technical">
      <summary>{{ t("pipelines.strategy_technical", "Technical details") }}</summary>
      <dl>
        <div>
          <dt>{{ t("pipelines.strategy_id", "Strategy ID") }}</dt>
          <dd>
            <code>{{ strategy.strategy_id }}</code> v{{ strategy.version }}
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.strategy_types", "Data types") }}</dt>
          <dd>
            <code>{{ strategy.input_type }}</code> → <code>{{ strategy.output_type }}</code>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.strategy_capabilities", "Capabilities") }}</dt>
          <dd>
            <code v-for="item in strategy.capabilities" :key="item">{{ item }}</code>
            <span v-if="!strategy.capabilities.length">—</span>
          </dd>
        </div>
        <div>
          <dt>{{ t("pipelines.strategy_settings", "Settings") }}</dt>
          <dd>
            <code v-for="key in configKeys" :key="key">{{ key }}</code>
            <span v-if="!configKeys.length">—</span>
          </dd>
        </div>
      </dl>
    </details>
  </aside>
</template>

<style scoped>
.strategy-inspector {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
@media (min-width: 1121px) {
  .strategy-inspector {
    position: sticky;
    top: var(--pipeline-studio-sticky-top, var(--space-3));
    max-height: var(
      --pipeline-studio-pane-max-height,
      calc(100dvh - var(--pipeline-studio-sticky-top, var(--space-3)) - var(--space-3))
    );
    overflow: auto;
    overscroll-behavior: contain;
  }
}
.strategy-inspector h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.25rem;
  line-height: var(--lh-tight);
}
.strategy-inspector header code,
.strategy-technical code {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.strategy-inspector h4 {
  margin: 0 0 var(--space-2);
  color: var(--text-primary);
  font-size: 1rem;
}
.strategy-inspector section {
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.description {
  margin: 0 0 var(--space-3);
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.strategy-inspector dl {
  display: grid;
  gap: var(--space-3);
  margin: 0;
}
.strategy-inspector dt {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.strategy-inspector dd {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
  overflow-wrap: anywhere;
}
.strategy-inspector dd code + code {
  margin-left: var(--space-2);
}
.with-help {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
}
.workflows,
.empty,
.usage-meta {
  margin: 0 0 var(--space-2);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.usage-list {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.usage-list li {
  display: grid;
}
.link-button {
  justify-self: start;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--accent-fg);
  font: inherit;
  font-size: 0.875rem;
  font-weight: var(--fw-bold);
  text-align: left;
  text-decoration: underline;
  cursor: pointer;
}
.link-button:focus-visible,
.strategy-technical summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.strategy-technical summary {
  width: fit-content;
  color: var(--text-primary);
  font-size: 0.9375rem;
  font-weight: var(--fw-bold);
  cursor: pointer;
}
.strategy-technical dl {
  margin-top: var(--space-2);
}
.port-rows {
  display: grid;
  gap: var(--space-1);
}
.port-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.block {
  display: block;
  color: var(--text-secondary);
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
</style>
