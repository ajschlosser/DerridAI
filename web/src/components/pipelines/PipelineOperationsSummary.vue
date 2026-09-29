<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import type { PipelineOperationalMetrics } from "../../types/pipelines";
import { useI18nStore } from "../../stores/i18n";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  metrics: PipelineOperationalMetrics;
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const failedRuns = computed(() => Number(props.metrics.status_counts.failed || 0));
const topStrategies = computed(() => props.metrics.strategies.slice(0, 10));

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

    <div v-if="metrics.sampled_run_count" class="metric-cards">
      <article>
        <span class="metric-label">
          {{ t("pipelines.metrics_runs", "Sampled runs") }}
          <UiTooltip
            :text="
              t(
                'pipelines.metrics_runs_help',
                'The newest pipeline traces included in this summary, up to the configured sample limit. This is an operational sample rather than a lifetime total.',
              )
            "
          />
        </span>
        <strong>{{ formatCount(metrics.sampled_run_count) }}</strong>
      </article>
      <article>
        <span class="metric-label">
          {{ t("pipelines.metrics_fallback_runs", "Runs with fallback or stage failure") }}
          <UiTooltip
            :text="
              t(
                'pipelines.metrics_fallback_runs_help',
                'A run is counted here when any stage failed, timed out, was unavailable, or recorded a fallback reason. The final run may still have completed successfully.',
              )
            "
          />
        </span>
        <strong>{{ formatCount(metrics.fallback_run_count) }}</strong>
      </article>
      <article>
        <span class="metric-label">
          {{ t("pipelines.metrics_failed_runs", "Failed runs") }}
          <UiTooltip
            :text="
              t(
                'pipelines.metrics_failed_runs_help',
                'Runs whose overall pipeline status is failed. A stage-level fallback does not automatically make the whole run a failure.',
              )
            "
          />
        </span>
        <strong>{{ formatCount(failedRuns) }}</strong>
      </article>
      <article>
        <span class="metric-label">
          {{ t("pipelines.metrics_p95_runtime", "95th-percentile run time") }}
          <UiTooltip
            :text="
              t(
                'pipelines.metrics_p95_runtime_help',
                'About 95% of sampled runs finished at or below this duration. It is useful for spotting slow-tail behavior that an average can hide.',
              )
            "
          />
        </span>
        <strong>{{ formatDuration(metrics.p95_run_elapsed_ms) }}</strong>
      </article>
    </div>

    <div v-if="metrics.sampled_run_count" class="metrics-grid">
      <section aria-labelledby="pipeline-feature-metrics-title">
        <h4 id="pipeline-feature-metrics-title">
          {{ t("pipelines.metrics_by_feature", "By feature") }}
        </h4>
        <div class="table-shell">
          <table>
            <thead>
              <tr>
                <th scope="col">{{ t("pipelines.metric_feature", "Feature") }}</th>
                <th scope="col">{{ t("pipelines.metric_runs", "Runs") }}</th>
                <th scope="col">{{ t("pipelines.metric_fallbacks", "Fallbacks") }}</th>
                <th scope="col">{{ t("pipelines.metric_failed", "Failed") }}</th>
                <th scope="col">{{ t("pipelines.metric_p95", "p95 time") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in metrics.features" :key="row.feature">
                <td>
                  <code>{{ row.feature }}</code>
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
                  <code>{{ row.strategy_id }}</code>
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
.metrics-workspace {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.metrics-workspace > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.metrics-workspace h3,
.metrics-workspace h4 {
  margin: 0;
}
.metrics-workspace h3 {
  font-size: 1rem;
}
.metrics-workspace h4 {
  font-size: 0.83rem;
}
.metrics-workspace header p,
.section-help,
.empty-state p {
  max-width: 800px;
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.5;
}
.sample-note {
  flex: 0 0 auto;
  color: var(--muted);
  font-size: 0.75rem;
}
.metric-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.metric-cards article {
  display: grid;
  gap: 5px;
  min-height: 76px;
  padding: 10px 11px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.metric-label {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 700;
}
.metric-cards strong {
  font-size: 1.15rem;
  font-variant-numeric: tabular-nums;
}
.metrics-grid {
  display: grid;
  gap: 15px;
}
.metrics-grid > section {
  display: grid;
  gap: 7px;
}
.table-shell {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 10px;
}
table {
  width: 100%;
  min-width: 620px;
  border-collapse: collapse;
  font-size: 0.76rem;
}
th,
td {
  padding: 8px 9px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th {
  background: var(--soft);
  color: var(--muted);
  font-weight: 750;
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
  color: var(--muted);
  font-size: 0.75rem;
}
.empty-state {
  padding: 12px 13px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
@media (max-width: 900px) {
  .metric-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .metrics-workspace > header {
    display: grid;
  }
  .metric-cards {
    grid-template-columns: 1fr;
  }
}
</style>
