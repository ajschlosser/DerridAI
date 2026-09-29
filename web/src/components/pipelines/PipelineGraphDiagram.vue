<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  PIPELINE_NODE_HEIGHT,
  PIPELINE_NODE_WIDTH,
  layoutPipelineDiagram,
  type PipelineEdgeKind,
} from "../../domain/pipelineGraph";
import {
  pipelineRunStatusLabel,
  pipelineStageFamilyLabel,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineRunTrace, PipelineStage, PipelineStrategy } from "../../types/pipelines";

const props = defineProps<{
  stages: PipelineStage[];
  entryStageIds: string[];
  strategies: PipelineStrategy[];
  execution?: PipelineRunTrace | null;
  title: string;
  description: string;
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const selectedId = ref("");

const diagram = computed(() =>
  layoutPipelineDiagram(props.stages, props.entryStageIds, props.execution || null),
);
const selected = computed(
  () =>
    diagram.value.nodes.find((node) => node.id === selectedId.value) ||
    diagram.value.nodes[0] ||
    null,
);

watch(
  diagram,
  (next) => {
    if (!next.nodes.some((node) => node.id === selectedId.value)) {
      selectedId.value = next.nodes[0]?.id || "";
    }
  },
  { immediate: true },
);

const edgeKinds: PipelineEdgeKind[] = [
  "next",
  "on_empty",
  "on_unavailable",
  "on_timeout",
  "on_error",
];

function edgeLabel(kind: PipelineEdgeKind) {
  const labels: Record<PipelineEdgeKind, string> = {
    next: t("pipelines.edge_next", "Next"),
    on_empty: t("pipelines.on_empty", "On empty"),
    on_unavailable: t("pipelines.on_unavailable", "On unavailable"),
    on_timeout: t("pipelines.on_timeout", "On timeout"),
    on_error: t("pipelines.on_error", "On error"),
  };
  return labels[kind];
}

function strategyFor(strategyId: string) {
  return props.strategies.find((item) => item.strategy_id === strategyId) || null;
}
function familyFor(strategyId: string) {
  return strategyFor(strategyId)?.family || "";
}
function labelFor(strategyId: string) {
  const strategy = strategyFor(strategyId);
  return strategy ? pipelineStrategyLabel(strategy, t) : strategyId;
}

function presenceLabel(presence: string) {
  if (presence === "not_reached") return t("pipelines.not_reached", "Not reached");
  if (presence === "observed_only") return t("pipelines.observed_only", "Observed only");
  return "";
}

function duration(value: number | null) {
  if (value == null) return "—";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(value < 10000 ? 2 : 1)} s`;
}
</script>

<template>
  <section class="pipeline-diagram" :aria-label="title">
    <header>
      <div>
        <h4>{{ title }}</h4>
        <p>{{ description }}</p>
      </div>
    </header>

    <div v-if="diagram.nodes.length" class="diagram-layout">
      <div class="diagram-scroll">
        <div
          class="diagram-canvas"
          :style="{ width: `${diagram.width}px`, height: `${diagram.height}px` }"
        >
          <svg
            class="diagram-edges"
            :viewBox="`0 0 ${diagram.width} ${diagram.height}`"
            aria-hidden="true"
          >
            <defs>
              <marker
                id="pipeline-arrow"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="7"
                markerHeight="7"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" />
              </marker>
            </defs>
            <path
              v-for="edge in diagram.edges"
              :key="edge.id"
              :d="edge.path"
              :data-kind="edge.kind"
              :data-traversed="edge.traversed ? 'true' : 'false'"
              marker-end="url(#pipeline-arrow)"
            />
          </svg>
          <button
            v-for="node in diagram.nodes"
            :key="node.id"
            type="button"
            class="diagram-node"
            :class="{ selected: selected?.id === node.id }"
            :style="{
              width: `${PIPELINE_NODE_WIDTH}px`,
              height: `${PIPELINE_NODE_HEIGHT}px`,
              transform: `translate(${node.x}px, ${node.y}px)`,
            }"
            :data-status="node.executionStatus || undefined"
            :data-presence="node.presence"
            :aria-pressed="selected?.id === node.id"
            @click="selectedId = node.id"
          >
            <span class="node-kicker">
              <span v-if="node.entry">{{ t("pipelines.node_entry", "Entry") }}</span>
              <span>{{ pipelineStageFamilyLabel(familyFor(node.strategy), t) }}</span>
            </span>
            <strong>{{ node.id }}</strong>
            <span>{{ labelFor(node.strategy) }}</span>
          </button>
        </div>
      </div>

      <aside
        v-if="selected"
        class="node-inspector"
        :aria-label="t('pipelines.selected_stage', 'Selected stage')"
      >
        <p class="inspector-kicker">{{ t("pipelines.selected_stage", "Selected stage") }}</p>
        <h5>{{ selected.id }}</h5>
        <dl>
          <div>
            <dt>{{ t("pipelines.term_strategy", "Strategy") }}</dt>
            <dd>{{ labelFor(selected.strategy) }}</dd>
          </div>
          <div>
            <dt>{{ t("pipelines.status", "Status") }}</dt>
            <dd>
              {{
                selected.executionStatus === "not_reached"
                  ? t("pipelines.not_reached", "Not reached")
                  : selected.executionStatus
                    ? pipelineRunStatusLabel(selected.executionStatus, t)
                    : selected.enabled
                      ? t("pipelines.status_active", "Active")
                      : t("pipelines.node_disabled", "Disabled")
              }}
              <span v-if="presenceLabel(selected.presence)">
                · {{ presenceLabel(selected.presence) }}</span
              >
            </dd>
          </div>
          <div v-if="execution">
            <dt>{{ t("pipelines.duration", "Duration") }}</dt>
            <dd>{{ duration(selected.elapsedMs) }}</dd>
          </div>
          <div v-if="execution">
            <dt>{{ t("pipelines.trace_counts", "In → out") }}</dt>
            <dd>{{ selected.inputCount ?? "—" }} → {{ selected.outputCount ?? "—" }}</dd>
          </div>
          <div v-if="selected.fallbackReason">
            <dt>{{ t("pipelines.term_edge", "Connection / edge") }}</dt>
            <dd>{{ selected.fallbackReason }}</dd>
          </div>
        </dl>
      </aside>
    </div>
    <p v-else class="diagram-empty">
      {{ t("pipelines.diagram_empty", "This pipeline has no stages to diagram.") }}
    </p>

    <ul class="diagram-legend">
      <li v-for="kind in edgeKinds" :key="kind" :data-kind="kind">{{ edgeLabel(kind) }}</li>
      <li v-if="execution" data-kind="not_reached">
        {{ t("pipelines.not_reached", "Not reached") }}
      </li>
      <li v-if="execution" data-kind="observed_only">
        {{ t("pipelines.observed_only", "Observed only") }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.pipeline-diagram {
  display: grid;
  gap: 12px;
}
.pipeline-diagram header h4 {
  margin: 0;
  font-size: 0.95rem;
}
.pipeline-diagram header p,
.diagram-empty {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.5;
}
.diagram-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 240px);
  gap: 12px;
  align-items: start;
}
.diagram-scroll {
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
}
.diagram-canvas {
  position: relative;
  min-width: 100%;
}
.diagram-edges {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.diagram-edges path {
  fill: none;
  stroke: var(--line-strong, var(--line));
  stroke-width: 1.5;
}
.diagram-edges path[data-kind="next"] {
  stroke: var(--text);
}
.diagram-edges path[data-kind="on_empty"] {
  stroke: var(--tone-warn-border);
  stroke-dasharray: 5 3;
}
.diagram-edges path[data-kind="on_unavailable"] {
  stroke: var(--tone-info-border);
  stroke-dasharray: 2 3;
}
.diagram-edges path[data-kind="on_timeout"] {
  stroke: var(--tone-warn-fg);
  stroke-dasharray: 8 3;
}
.diagram-edges path[data-kind="on_error"] {
  stroke: var(--tone-danger-border);
  stroke-dasharray: 1 3;
}
.diagram-edges path[data-traversed="true"] {
  stroke-width: 2.25;
}
.diagram-edges marker path {
  fill: var(--text);
}
.diagram-node {
  position: absolute;
  display: grid;
  align-content: center;
  gap: 2px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.diagram-node strong,
.diagram-node span {
  overflow: hidden;
  font-size: 0.75rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.diagram-node .node-kicker,
.diagram-node span:last-child {
  color: var(--muted);
}
.diagram-node.selected {
  border-color: var(--text);
  outline: 2px solid var(--text);
  outline-offset: 1px;
}
.diagram-node:focus-visible {
  outline: 2px solid var(--text);
  outline-offset: 2px;
}
.diagram-node[data-status="completed"] {
  background: var(--tone-ok-bg);
  border-color: var(--tone-ok-border);
}
.diagram-node[data-status="failed"],
.diagram-node[data-status="timed_out"] {
  background: var(--tone-danger-bg);
  border-color: var(--tone-danger-border);
}
.diagram-node[data-status="unavailable"],
.diagram-node[data-status="skipped"] {
  background: var(--tone-warn-bg);
  border-color: var(--tone-warn-border);
}
.diagram-node[data-presence="not_reached"] {
  opacity: 0.72;
}
.diagram-node[data-presence="observed_only"] {
  border-style: dashed;
}
.node-inspector {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.inspector-kicker,
.node-inspector dt {
  color: var(--muted);
  font-size: 0.75rem;
}
.node-inspector h5 {
  margin: 0;
  font-size: 0.95rem;
}
.node-inspector dl {
  display: grid;
  gap: 8px;
  margin: 0;
}
.node-inspector dd {
  margin: 0;
  font-size: 0.78rem;
}
.diagram-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--muted);
  font-size: 0.75rem;
}
.diagram-legend li::before {
  display: inline-block;
  width: 18px;
  margin-right: 6px;
  border-top: 2px solid var(--text);
  content: "";
  transform: translateY(-3px);
}
.diagram-legend li[data-kind="on_empty"]::before {
  border-top-style: dashed;
  border-top-color: var(--tone-warn-border);
}
.diagram-legend li[data-kind="on_unavailable"]::before {
  border-top-style: dotted;
  border-top-color: var(--tone-info-border);
}
.diagram-legend li[data-kind="on_timeout"]::before {
  border-top-style: dashed;
  border-top-color: var(--tone-warn-fg);
}
.diagram-legend li[data-kind="on_error"]::before {
  border-top-color: var(--tone-danger-border);
}
.diagram-legend li[data-kind="not_reached"]::before,
.diagram-legend li[data-kind="observed_only"]::before {
  border-top-style: dashed;
  border-top-color: var(--muted);
}
@media (max-width: 860px) {
  .diagram-layout {
    grid-template-columns: 1fr;
  }
}
</style>
