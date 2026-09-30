<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import type { PipelineGraphNode } from "../../domain/pipelineGraph";
import {
  pipelineDataTypeLabel,
  pipelineRunStatusLabel,
  pipelineStageFamilyLabel,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import { pipelineRunTone } from "../../domain/pipelineStudioPresentation";
import { findTerm, termLabel } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineStrategy, PipelineWorkflowVocabulary } from "../../types/pipelines";

const props = defineProps<{
  node: PipelineGraphNode;
  strategy: PipelineStrategy | null;
  vocabulary?: PipelineWorkflowVocabulary;
  /** True when the node belongs to an execution, which adds timing and counts. */
  hasExecution?: boolean;
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const strategyLabel = computed(() =>
  props.strategy ? pipelineStrategyLabel(props.strategy, t) : props.node.strategy,
);
const phaseLabel = computed(() => {
  const term = findTerm(props.vocabulary?.phases, props.strategy?.phase);
  return term ? termLabel(term, t) : "";
});
const effectNote = computed(() => {
  const term = findTerm(props.vocabulary?.effect_notes, props.strategy?.effect_note);
  return term ? termLabel(term, t) : "";
});
const statusText = computed(() => {
  const { executionStatus, enabled } = props.node;
  if (executionStatus === "not_reached") return t("pipelines.not_reached", "Not reached");
  if (executionStatus) return pipelineRunStatusLabel(executionStatus, t);
  return enabled
    ? t("pipelines.status_active", "Active")
    : t("pipelines.node_disabled", "Disabled");
});
const statusTone = computed(() => {
  if (props.node.executionStatus && props.node.executionStatus !== "not_reached")
    return pipelineRunTone(props.node.executionStatus);
  if (props.node.executionStatus === "not_reached") return "neutral";
  return props.node.enabled ? "success" : "warning";
});
const presenceText = computed(() => {
  if (props.node.presence === "not_reached") return t("pipelines.not_reached", "Not reached");
  if (props.node.presence === "observed_only") return t("pipelines.observed_only", "Observed only");
  return "";
});

function duration(value: number | null) {
  if (value == null) return t("pipelines.duration_unknown", "Unknown");
  if (value < 1000) return `${Math.round(value)} ${t("pipelines.duration_milliseconds", "ms")}`;
  return `${(value / 1000).toFixed(value < 10000 ? 2 : 1)} ${t("pipelines.duration_seconds", "s")}`;
}
</script>

<template>
  <aside class="stage-inspector" :aria-label="t('pipelines.selected_stage', 'Selected stage')">
    <p class="inspector-kicker">{{ t("pipelines.selected_stage", "Selected stage") }}</p>
    <h5>{{ node.id }}</h5>
    <p class="inspector-status">
      <UiStatusBadge :label="statusText" :tone="statusTone" />
      <span v-if="node.entry" class="inspector-flag">{{ t("pipelines.node_entry", "Entry") }}</span>
      <span v-if="presenceText" class="inspector-flag">{{ presenceText }}</span>
    </p>
    <dl>
      <div>
        <dt>{{ t("pipelines.term_strategy", "Strategy") }}</dt>
        <dd>
          {{ strategyLabel }}
          <code v-if="strategy" class="inspector-id">{{ strategy.strategy_id }}</code>
        </dd>
      </div>
      <div v-if="strategy">
        <dt>{{ t("pipelines.strategy_family", "Family") }}</dt>
        <dd>
          {{ pipelineStageFamilyLabel(strategy.family, t) }}
          <span v-if="phaseLabel" class="inspector-muted"> · {{ phaseLabel }}</span>
        </dd>
      </div>
      <div v-if="effectNote">
        <dt>{{ t("pipelines.scholarly_effect", "Scholarly effect") }}</dt>
        <dd>{{ effectNote }}</dd>
      </div>
      <div v-if="strategy">
        <dt>{{ t("pipelines.strategy_io", "Input → output") }}</dt>
        <dd>
          {{ pipelineDataTypeLabel(strategy.input_type, t) }} →
          {{ pipelineDataTypeLabel(strategy.output_type, t) }}
        </dd>
      </div>
      <div v-if="hasExecution">
        <dt>{{ t("pipelines.duration", "Duration") }}</dt>
        <dd>{{ duration(node.elapsedMs) }}</dd>
      </div>
      <div v-if="hasExecution">
        <dt>{{ t("pipelines.trace_counts", "In → out") }}</dt>
        <dd>{{ node.inputCount ?? "—" }} → {{ node.outputCount ?? "—" }}</dd>
      </div>
      <div v-if="node.fallbackReason">
        <dt>{{ t("pipelines.term_edge", "Connection / edge") }}</dt>
        <dd>{{ node.fallbackReason }}</dd>
      </div>
    </dl>
  </aside>
</template>

<style scoped>
.stage-inspector {
  display: grid;
  align-content: start;
  gap: var(--space-2);
  min-width: 0;
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.inspector-kicker {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.stage-inspector h5 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.0625rem;
  overflow-wrap: anywhere;
}
.inspector-status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
}
.inspector-flag,
.inspector-muted {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.stage-inspector dl {
  display: grid;
  gap: var(--space-3);
  margin: var(--space-2) 0 0;
}
.stage-inspector dt {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.stage-inspector dd {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
  overflow-wrap: anywhere;
}
.inspector-id {
  display: block;
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
</style>
