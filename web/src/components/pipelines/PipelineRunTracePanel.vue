<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineRunTrace, PipelineStageTrace } from "../../types/pipelines";

const props = defineProps<{
  trace: PipelineRunTrace;
}>();

const i18n = useI18nStore();
const completedStages = computed(
  () => props.trace.stages.filter((stage) => stage.status === "completed").length,
);

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}
function ms(value?: number | null) {
  if (value === null || value === undefined) return "—";
  if (value < 1000) return `${Math.max(0, Math.round(value))} ms`;
  return `${(value / 1000).toFixed(value < 10000 ? 2 : 1)} s`;
}
function count(value?: number | null) {
  return value === null || value === undefined ? "—" : Number(value).toLocaleString(i18n.locale);
}
function statusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: t("pipelines.status_completed", "Completed"),
    skipped: t("pipelines.status_skipped", "Skipped"),
    unavailable: t("pipelines.status_unavailable", "Unavailable"),
    timed_out: t("pipelines.status_timed_out", "Timed out"),
    failed: t("pipelines.status_failed", "Failed"),
    running: t("pipelines.status_running", "Running"),
    pending: t("pipelines.status_pending", "Pending"),
  };
  return labels[status] || status;
}
function stageDetail(stage: PipelineStageTrace) {
  return [stage.provider, stage.model, stage.collection].filter(Boolean).join(" · ");
}
</script>

<template>
  <article class="trace-panel" :aria-labelledby="`trace-${trace.run_id}`">
    <header class="trace-header">
      <div>
        <div class="eyebrow">{{ t("pipelines.execution_trace", "Execution trace") }}</div>
        <h3 :id="`trace-${trace.run_id}`">
          {{ trace.pipeline_id }} <span>v{{ trace.pipeline_version }}</span>
        </h3>
        <p>
          {{ trace.run_id }} · {{ completedStages }}/{{ trace.stages.length }}
          {{ t("pipelines.stages_completed", "stages completed") }}
        </p>
        <p class="trace-explainer">
          {{
            t(
              "pipelines.trace_plain_help",
              "This is the historical record of what actually happened during the run. It is not merely the saved design: skipped steps, fallbacks, models, counts, and timings reflect runtime behavior.",
            )
          }}
        </p>
      </div>
      <div class="trace-summary">
        <span class="status-pill" :data-status="trace.status">{{ statusLabel(trace.status) }}</span>
        <strong>{{ ms(trace.total_elapsed_ms) }}</strong>
      </div>
    </header>

    <ol class="trace-stages">
      <li v-for="(stage, index) in trace.stages" :key="`${stage.stage_id}:${index}`">
        <div class="trace-marker" :data-status="stage.status" aria-hidden="true">
          <AppIcon
            :name="
              stage.status === 'completed'
                ? 'check'
                : stage.status === 'failed' || stage.status === 'timed_out'
                  ? 'warning'
                  : 'record'
            "
          />
        </div>
        <div class="trace-stage">
          <div class="trace-stage-heading">
            <div>
              <strong class="trace-label-with-help">
                {{ stage.strategy_id }}
                <UiTooltip
                  :text="
                    t(
                      'pipelines.trace_strategy_help',
                      'The strategy ID is the technical name of the registered operation that ran at this step.',
                    )
                  "
                />
              </strong>
              <code class="trace-label-with-help">
                {{ stage.stage_id }}
                <UiTooltip
                  :text="
                    t(
                      'pipelines.trace_stage_id_help',
                      'The stage ID identifies this specific step inside the saved pipeline version. It lets you match the runtime trace back to the pipeline definition.',
                    )
                  "
                />
              </code>
            </div>
            <div class="trace-stage-metrics">
              <span>{{ statusLabel(stage.status) }}</span>
              <span class="trace-label-with-help">
                {{ ms(stage.elapsed_ms) }}
                <UiTooltip
                  :text="
                    t(
                      'pipelines.trace_elapsed_help',
                      'Elapsed time is the measured runtime for this stage when DerridAI could attribute a duration to it. A dash means the duration was not separately measured.',
                    )
                  "
                />
              </span>
            </div>
          </div>

          <p v-if="stageDetail(stage)" class="trace-meta">{{ stageDetail(stage) }}</p>
          <div v-if="stage.input_count != null || stage.output_count != null" class="trace-counts">
            <span>
              {{ t("pipelines.input", "Input") }}
              <UiTooltip
                :text="
                  t(
                    'pipelines.trace_input_help',
                    'How many items entered this stage, when the stage reports a count. The items may be candidate records, passages, or another stage-specific data type.',
                  )
                "
              />
              <strong>{{ count(stage.input_count) }}</strong>
            </span>
            <span aria-hidden="true">→</span>
            <span>
              {{ t("pipelines.output", "Output") }}
              <UiTooltip
                :text="
                  t(
                    'pipelines.trace_output_help',
                    'How many items left this stage. A smaller output than input often means filtering, reranking truncation, validation, or selection reduced the candidate set.',
                  )
                "
              />
              <strong>{{ count(stage.output_count) }}</strong>
            </span>
          </div>

          <p v-if="stage.fallback_reason" class="trace-warning">
            <AppIcon name="warning" />
            <span>
              <strong>{{ t("pipelines.fallback", "Fallback") }}:</strong>
              {{ stage.fallback_reason }}
            </span>
          </p>
          <ul v-if="stage.warnings?.length" class="trace-warning-list">
            <li v-for="warning in stage.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </div>
      </li>
    </ol>

    <details v-if="trace.warnings?.length" class="run-warnings">
      <summary>
        {{ t("pipelines.run_warnings", "Run warnings") }} ({{ trace.warnings.length }})
      </summary>
      <ul>
        <li v-for="warning in trace.warnings" :key="warning">{{ warning }}</li>
      </ul>
    </details>
  </article>
</template>

<style scoped>
.trace-panel {
  display: grid;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.trace-header,
.trace-stage-heading,
.trace-stage-metrics,
.trace-counts {
  display: flex;
  align-items: center;
}
.trace-header {
  justify-content: space-between;
  gap: 16px;
}
.eyebrow {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.trace-header h3 {
  margin: 3px 0 0;
  font-size: 1rem;
}
.trace-header h3 span,
.trace-header p {
  color: var(--muted);
  font-weight: 500;
}
.trace-header p {
  margin: 4px 0 0;
  font-size: 0.76rem;
}
.trace-header .trace-explainer {
  max-width: 720px;
  line-height: 1.45;
}
.trace-summary {
  display: grid;
  gap: 4px;
  justify-items: end;
  font-size: 0.8rem;
}
.status-pill {
  padding: 3px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--soft);
  font-size: 0.75rem;
  font-weight: 750;
}
.status-pill[data-status="completed"] {
  border-color: color-mix(in srgb, var(--line) 65%, currentColor);
}
.trace-stages {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}
.trace-stages > li {
  position: relative;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 10px;
}
.trace-stages > li:not(:last-child)::before {
  position: absolute;
  top: 28px;
  bottom: -2px;
  left: 14px;
  width: 1px;
  background: var(--line);
  content: "";
}
.trace-marker {
  z-index: 1;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--card);
}
.trace-marker :deep(svg) {
  width: 13px;
  height: 13px;
}
.trace-marker[data-status="skipped"],
.trace-marker[data-status="pending"] {
  color: var(--muted);
}
.trace-marker[data-status="failed"],
.trace-marker[data-status="timed_out"],
.trace-marker[data-status="unavailable"] {
  background: var(--soft);
}
.trace-stage {
  min-width: 0;
  padding: 3px 0 15px;
}
.trace-stage-heading {
  justify-content: space-between;
  gap: 12px;
}
.trace-stage-heading strong,
.trace-stage-heading code {
  display: block;
}
.trace-label-with-help {
  display: inline-flex !important;
  align-items: center;
  gap: 2px;
}
.trace-stage-heading strong {
  font-size: 0.82rem;
}
.trace-stage-heading code {
  margin-top: 2px;
  color: var(--muted);
  font-size: 0.75rem;
}
.trace-stage-metrics {
  flex-wrap: wrap;
  justify-content: end;
  gap: 8px;
  color: var(--muted);
  font-size: 0.75rem;
}
.trace-meta {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 0.76rem;
}
.trace-counts {
  gap: 7px;
  margin-top: 7px;
  color: var(--muted);
  font-size: 0.75rem;
}
.trace-counts strong {
  color: inherit;
}
.trace-warning {
  display: flex;
  gap: 7px;
  margin: 8px 0 0;
  padding: 8px 9px;
  border-radius: 8px;
  background: var(--soft);
  font-size: 0.75rem;
  line-height: 1.4;
}
.trace-warning :deep(svg) {
  flex: 0 0 auto;
  width: 14px;
  height: 14px;
  margin-top: 1px;
}
.trace-warning-list,
.run-warnings ul {
  margin: 7px 0 0;
  padding-left: 18px;
  color: var(--muted);
  font-size: 0.75rem;
}
.run-warnings {
  border-top: 1px solid var(--line);
  padding-top: 10px;
}
.run-warnings summary {
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 700;
}
@media (max-width: 640px) {
  .trace-header,
  .trace-stage-heading {
    align-items: start;
  }
  .trace-header {
    display: grid;
  }
  .trace-summary {
    justify-items: start;
  }
  .trace-stage-heading {
    display: grid;
  }
  .trace-stage-metrics {
    justify-content: start;
  }
}
</style>
