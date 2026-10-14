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
import { pipelineStrategyLabel } from "../../domain/pipelinePresentation";
import {
  pipelineOperationalAttention,
  type OperationalAttentionRow,
} from "../../domain/pipelineStudioPresentation";
import {
  findTerm,
  purposeForFeature,
  purposeText,
  termLabel,
} from "../../domain/pipelineWorkflows";
import type {
  PipelineOperationalMetrics,
  PipelinePurpose,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  metrics: PipelineOperationalMetrics;
  strategies?: PipelineStrategy[];
  purposes?: PipelinePurpose[];
  vocabulary?: PipelineWorkflowVocabulary;
}>();

const emit = defineEmits<{
  /** Open the executions of one workflow category; the server supports this filter. */
  viewExecutions: [category: string];
  viewStrategy: [strategyId: string];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const attention = computed(() => pipelineOperationalAttention(props.metrics).slice(0, 10));
function attentionLabel(row: OperationalAttentionRow) {
  return row.kind === "workflow" ? workflowLabel(row.id) : strategyLabel(row.id) || row.id;
}

const failedRuns = computed(() => Number(props.metrics.status_counts.failed || 0));
const topStrategies = computed(() => props.metrics.strategies.slice(0, 10));

function workflowLabel(category: string) {
  const term = findTerm(props.vocabulary?.categories, category);
  return term ? termLabel(term, t) : t("pipelines.unregistered_purpose", "Unregistered purpose");
}

function featureLabel(feature: string) {
  const purpose = purposeForFeature(props.purposes || [], feature);
  return purpose ? purposeText(purpose, "label", t) : "";
}

function strategyLabel(strategyId: string) {
  const strategy = (props.strategies || []).find((item) => item.strategy_id === strategyId);
  return strategy ? pipelineStrategyLabel(strategy, t) : "";
}

function formatDuration(value: number | null | undefined) {
  if (value == null) return "—";
  if (value < 1000) return `${Math.round(value)} ms`;
  if (value < 60000) return `${(value / 1000).toFixed(value < 10000 ? 1 : 0)} s`;
  return `${(value / 60000).toFixed(1)} min`;
}

function formatCount(value: number | null | undefined) {
  return value == null ? "—" : new Intl.NumberFormat(i18n.locale).format(value);
}
</script>

<template>
  <section class="metrics-workspace" aria-labelledby="pipeline-metrics-title">
    <header>
      <div>
        <h3 id="pipeline-metrics-title">
          {{ t("pipelines.metrics_title", "Operational health") }}
        </h3>
        <p>
          {{
            t(
              "pipelines.metrics_help",
              "Aggregated from recent execution traces. These numbers describe system behavior—latency, failures, and fallbacks—not the scholarly validity of retrieved evidence.",
            )
          }}
        </p>
      </div>
      <span class="sample-note">
        {{ t("pipelines.metrics_sample", "Recent trace sample") }}:
        <strong>{{ formatCount(metrics.sampled_run_count) }}</strong>
        /
        {{ formatCount(metrics.sample_limit) }}
      </span>
    </header>

    <dl v-if="metrics.sampled_run_count" class="metric-summary">
      <div>
        <dt class="metric-label">
          {{ t("pipelines.metrics_runs", "Sampled runs") }}
          <UiTooltip
            :text="
              t(
                'pipelines.metrics_runs_help',
                'The newest pipeline traces included in this summary, up to the configured sample limit. This is an operational sample rather than a lifetime total.',
              )
            "
          />
        </dt>
        <dd>{{ formatCount(metrics.sampled_run_count) }}</dd>
      </div>
      <div>
        <dt class="metric-label">
          {{ t("pipelines.metrics_failed_runs", "Failed runs") }}
          <UiTooltip
            :text="
              t(
                'pipelines.metrics_failed_runs_help',
                'Runs whose overall pipeline status is failed. A stage-level fallback does not automatically make the whole run a failure.',
              )
            "
          />
        </dt>
        <dd>{{ formatCount(failedRuns) }}</dd>
      </div>
      <div>
        <dt class="metric-label">
          {{ t("pipelines.metrics_fallback_runs", "Runs with fallback or stage failure") }}
          <UiTooltip
            :text="
              t(
                'pipelines.metrics_fallback_runs_help',
                'A run is counted here when any stage failed, timed out, was unavailable, or recorded a fallback reason. The final run may still have completed successfully.',
              )
            "
          />
        </dt>
        <dd>{{ formatCount(metrics.fallback_run_count) }}</dd>
      </div>
      <div>
        <dt class="metric-label">
          {{ t("pipelines.metrics_p95_runtime", "95th-percentile run time") }}
          <UiTooltip
            :text="
              t(
                'pipelines.metrics_p95_runtime_help',
                'About 95% of sampled runs finished at or below this duration. It is useful for spotting slow-tail behavior that an average can hide.',
              )
            "
          />
        </dt>
        <dd>{{ formatDuration(metrics.p95_run_elapsed_ms) }}</dd>
      </div>
    </dl>

    <section
      v-if="metrics.sampled_run_count"
      class="attention"
      aria-labelledby="pipeline-attention-title"
    >
      <h4 id="pipeline-attention-title">{{ t("pipelines.needs_attention", "Needs attention") }}</h4>
      <p v-if="!attention.length" class="section-help">
        {{
          t(
            "pipelines.needs_attention_none",
            "No failures, issues, or fallbacks in the recent sample.",
          )
        }}
      </p>
      <div v-else class="table-shell">
        <table>
          <thead>
            <tr>
              <th scope="col">{{ t("pipelines.attention_subject", "Strategy / workflow") }}</th>
              <th scope="col">{{ t("pipelines.metric_executions", "Executions") }}</th>
              <th scope="col">{{ t("pipelines.metric_failed", "Failed") }}</th>
              <th scope="col">{{ t("pipelines.metric_fallbacks", "Fallbacks") }}</th>
              <th scope="col">{{ t("pipelines.metric_p95", "p95 time") }}</th>
              <th scope="col">{{ t("pipelines.attention_action", "Action") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in attention" :key="`${row.kind}:${row.id}`" :data-kind="row.kind">
              <td>
                <strong>{{ attentionLabel(row) }}</strong>
                <small>
                  {{
                    row.kind === "workflow"
                      ? t("pipelines.attention_workflow", "Workflow")
                      : t("pipelines.attention_strategy", "Strategy")
                  }}
                </small>
              </td>
              <td>{{ formatCount(row.executions) }}</td>
              <td>{{ formatCount(row.failures) }}</td>
              <td>{{ formatCount(row.fallbacks) }}</td>
              <td>{{ formatDuration(row.p95Ms) }}</td>
              <td>
                <UiButton
                  v-if="row.kind === 'workflow'"
                  size="small"
                  :label="t('pipelines.view_executions', 'View executions')"
                  @click="emit('viewExecutions', row.id)"
                />
                <UiButton
                  v-else
                  size="small"
                  :label="t('pipelines.view_strategy', 'View strategy')"
                  @click="emit('viewStrategy', row.id)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="metrics.sampled_run_count" class="metrics-grid">
      <section v-if="metrics.workflows?.length" aria-labelledby="pipeline-workflow-metrics-title">
        <h4 id="pipeline-workflow-metrics-title">
          {{ t("pipelines.metrics_by_workflow", "By workflow") }}
        </h4>
        <div class="table-shell">
          <table>
            <thead>
              <tr>
                <th scope="col">{{ t("pipelines.used_for", "Used for") }}</th>
                <th scope="col">{{ t("pipelines.metric_runs", "Runs") }}</th>
                <th scope="col">{{ t("pipelines.metric_fallbacks", "Fallbacks") }}</th>
                <th scope="col">{{ t("pipelines.metric_failed", "Failed") }}</th>
                <th scope="col">{{ t("pipelines.metric_p95", "p95 time") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in metrics.workflows"
                :key="row.category"
                :data-category="row.category"
              >
                <td>
                  <strong>{{ workflowLabel(row.category) }}</strong>
                  <small>
                    {{ row.features.map((feature) => featureLabel(feature) || feature).join(", ") }}
                  </small>
                </td>
                <td>{{ formatCount(row.run_count) }}</td>
                <td>{{ formatCount(row.fallback_run_count) }}</td>
                <td>{{ formatCount(row.failed_count) }}</td>
                <td>{{ formatDuration(row.p95_elapsed_ms) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="pipeline-feature-metrics-title">
        <h4 id="pipeline-feature-metrics-title">
          {{ t("pipelines.metrics_by_purpose", "By purpose") }}
        </h4>
        <div class="table-shell">
          <table>
            <thead>
              <tr>
                <th scope="col">{{ t("pipelines.filter_purpose", "Purpose") }}</th>
                <th scope="col">{{ t("pipelines.metric_runs", "Runs") }}</th>
                <th scope="col">{{ t("pipelines.metric_fallbacks", "Fallbacks") }}</th>
                <th scope="col">{{ t("pipelines.metric_failed", "Failed") }}</th>
                <th scope="col">{{ t("pipelines.metric_p95", "p95 time") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in metrics.features" :key="row.feature">
                <td>
                  <span v-if="featureLabel(row.feature)">{{ featureLabel(row.feature) }}</span>
                  <code :class="{ secondary: featureLabel(row.feature) }">{{ row.feature }}</code>
                </td>
                <td>{{ formatCount(row.run_count) }}</td>
                <td>{{ formatCount(row.fallback_run_count) }}</td>
                <td>{{ formatCount(row.failed_count) }}</td>
                <td>{{ formatDuration(row.p95_elapsed_ms) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="pipeline-strategy-metrics-title">
        <h4 id="pipeline-strategy-metrics-title">
          {{ t("pipelines.metrics_by_strategy", "Stage strategy health") }}
        </h4>
        <p class="section-help">
          {{
            t(
              "pipelines.metrics_by_strategy_help",
              "Strategies with failures or fallbacks are shown first. A strategy can appear under several stage IDs and pipeline versions.",
            )
          }}
        </p>
        <div class="table-shell">
          <table>
            <thead>
              <tr>
                <th scope="col">{{ t("pipelines.metric_strategy", "Strategy") }}</th>
                <th scope="col">{{ t("pipelines.metric_executions", "Executions") }}</th>
                <th scope="col">{{ t("pipelines.metric_issues", "Issues") }}</th>
                <th scope="col">{{ t("pipelines.metric_fallbacks", "Fallbacks") }}</th>
                <th scope="col">{{ t("pipelines.metric_p95", "p95 time") }}</th>
                <th scope="col">{{ t("pipelines.metric_flow", "Avg. in → out") }}</th>
                <th scope="col">{{ t("pipelines.metric_model_calls", "Model calls") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in topStrategies" :key="row.strategy_id">
                <td>
                  <span v-if="strategyLabel(row.strategy_id)">{{
                    strategyLabel(row.strategy_id)
                  }}</span>
                  <code :class="{ secondary: strategyLabel(row.strategy_id) }">{{
                    row.strategy_id
                  }}</code>
                  <small v-if="row.stage_ids.length">{{ row.stage_ids.join(", ") }}</small>
                </td>
                <td>{{ formatCount(row.executions) }}</td>
                <td>{{ formatCount(row.issue_count) }}</td>
                <td>{{ formatCount(row.fallback_count) }}</td>
                <td>{{ formatDuration(row.p95_elapsed_ms) }}</td>
                <td>
                  {{ formatCount(row.average_input_count) }}
                  <span aria-hidden="true">→</span>
                  {{ formatCount(row.average_output_count) }}
                </td>
                <td>{{ formatCount(row.model_call_count) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div v-else class="empty-state">
      <strong>{{ t("pipelines.metrics_empty", "No execution metrics yet") }}</strong>
      <p>
        {{
          t(
            "pipelines.metrics_empty_help",
            "Metrics will appear after pipeline-enabled features produce execution traces.",
          )
        }}
      </p>
    </div>
  </section>
</template>

<style scoped>
code.secondary {
  display: block;
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.metrics-workspace {
  display: grid;
  gap: var(--space-4);
}
.metrics-workspace > header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.metrics-workspace h3,
.metrics-workspace h4 {
  margin: 0;
  color: var(--text-primary);
}
.metrics-workspace h3 {
  font-size: 1.125rem;
}
.metrics-workspace h4 {
  font-size: 1rem;
}
.metrics-workspace header p,
.section-help,
.empty-state p {
  max-width: var(--measure);
  margin: var(--space-1) 0 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.sample-note {
  flex: 0 0 auto;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.metric-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3) var(--space-6, 28px);
  margin: 0;
  padding: var(--space-3) 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}
.metric-summary > div {
  display: grid;
  gap: 2px;
}
.metric-summary dd {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.375rem;
  font-weight: var(--fw-bold);
  font-variant-numeric: tabular-nums;
}
.metric-label {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.attention,
.metrics-grid > section {
  display: grid;
  gap: var(--space-2);
}
.metrics-grid {
  display: grid;
  gap: var(--space-5, 20px);
}
.table-shell {
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
table {
  width: 100%;
  min-width: 620px;
  border-collapse: collapse;
  font-size: 0.875rem;
}
th,
td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  text-align: left;
  vertical-align: top;
}
th {
  background: var(--surface-inset);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
tbody tr:last-child td {
  border-bottom: 0;
}
td code {
  font-size: 0.75rem;
}
td small {
  display: block;
  margin-top: 2px;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.empty-state {
  padding: var(--space-3) var(--space-4);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-card);
}
</style>
