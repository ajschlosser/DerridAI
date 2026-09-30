<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, useId, watch } from "vue";
import UiRelationNodeShell from "../relations/UiRelationNodeShell.vue";
import UiRelationToolbar from "../relations/UiRelationToolbar.vue";
import UiRelationViewport from "../relations/UiRelationViewport.vue";
import { useRelationLayoutState } from "../../composables/relations/useRelationLayoutState";
import { relationBoundsForPoints } from "../../domain/relations/geometry";
import {
  PIPELINE_NODE_HEIGHT,
  PIPELINE_NODE_WIDTH,
  layoutPipelineDiagram,
  pipelineEdgePath,
  type PipelineDiagramOrientation,
  type PipelineEdgeKind,
} from "../../domain/pipelineGraph";
import {
  pipelineRunStatusLabel,
  pipelineStageFamilyLabel,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineRunTrace, PipelineStage, PipelineStrategy } from "../../types/pipelines";
import UiTooltipInfobox, { type TooltipInfoboxRow } from "../ui/UiTooltipInfobox.vue";

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
const hoveredId = ref("");
const orientation = ref<PipelineDiagramOrientation>("horizontal");
const viewport = ref<InstanceType<typeof UiRelationViewport> | null>(null);
const arrowMarkerId = `pipeline-arrow-${useId()}`;
const layoutState = useRelationLayoutState();

const diagram = computed(() =>
  layoutPipelineDiagram(
    props.stages,
    props.entryStageIds,
    props.execution || null,
    orientation.value,
  ),
);
const nodes = computed(() =>
  diagram.value.nodes.map((node) => ({
    ...node,
    ...layoutState.positionFor(node.id, { x: node.x, y: node.y }),
  })),
);
const edges = computed(() => {
  const byId = new Map(nodes.value.map((node) => [node.id, node]));
  return diagram.value.edges.map((edge) => ({
    ...edge,
    path: pipelineEdgePath(byId.get(edge.from)!, byId.get(edge.to)!),
  }));
});
const selected = computed(
  () => nodes.value.find((node) => node.id === selectedId.value) || nodes.value[0] || null,
);
const contentBounds = computed(() => {
  const points = nodes.value.flatMap((node) => [
    { x: node.x, y: node.y },
    { x: node.x + PIPELINE_NODE_WIDTH, y: node.y + PIPELINE_NODE_HEIGHT },
  ]);
  return (
    relationBoundsForPoints(points, 28) || {
      x: 0,
      y: 0,
      width: diagram.value.width,
      height: diagram.value.height,
    }
  );
});
const viewportHeight = computed(() =>
  Math.min(620, Math.max(320, diagram.value.height + 40)),
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

watch(
  () => [props.stages, props.entryStageIds],
  () => layoutState.clearPositions(),
  { deep: true },
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
  if (value == null) return t("pipelines.duration_unknown", "Unknown");
  if (value < 1000) return `${Math.round(value)} ${t("pipelines.duration_milliseconds", "ms")}`;
  return `${(value / 1000).toFixed(value < 10000 ? 2 : 1)} ${t("pipelines.duration_seconds", "s")}`;
}

function statusLabel(node: (typeof nodes.value)[number]) {
  return node.executionStatus === "not_reached"
    ? t("pipelines.not_reached", "Not reached")
    : node.executionStatus
      ? pipelineRunStatusLabel(node.executionStatus, t)
      : node.enabled
        ? t("pipelines.status_active", "Active")
        : t("pipelines.node_disabled", "Disabled");
}

function infoRows(node: (typeof nodes.value)[number]): TooltipInfoboxRow[] {
  const rows: TooltipInfoboxRow[] = [
    { label: t("pipelines.status", "Status"), value: statusLabel(node) },
    { label: t("pipelines.term_strategy", "Strategy"), value: labelFor(node.strategy) },
  ];
  if (node.elapsedMs != null)
    rows.push({ label: t("pipelines.duration", "Duration"), value: duration(node.elapsedMs) });
  if (node.inputCount != null || node.outputCount != null)
    rows.push({
      label: t("pipelines.trace_counts", "In → out"),
      value: `${node.inputCount ?? "—"} → ${node.outputCount ?? "—"}`,
    });
  if (node.fallbackReason)
    rows.push({
      label: t("pipelines.term_edge", "Connection / edge"),
      value: node.fallbackReason,
    });
  return rows;
}

function moveNode(id: string, point: { x: number; y: number }) {
  layoutState.setPosition(id, point);
  selectedId.value = id;
}

function fitView() {
  viewport.value?.fitView(contentBounds.value);
}

function resetLayout() {
  layoutState.clearPositions();
  viewport.value?.resetView();
}

function chooseOrientation(next: PipelineDiagramOrientation) {
  if (orientation.value === next) return;
  orientation.value = next;
  layoutState.clearPositions();
  void nextTick(() => viewport.value?.fitView(contentBounds.value));
}
</script>

<template>
  <section class="pipeline-diagram" :aria-label="title">
    <header>
      <div>
        <h4>{{ title }}</h4>
        <p>{{ description }}</p>
      </div>
      <div class="diagram-control-stack">
        <div
          class="diagram-controls"
          role="group"
          :aria-label="t('pipelines.diagram_orientation', 'Diagram orientation')"
        >
          <button
            type="button"
            :aria-pressed="orientation === 'horizontal'"
            :class="{ selected: orientation === 'horizontal' }"
            @click="chooseOrientation('horizontal')"
          >
            {{ t("pipelines.diagram_horizontal", "Horizontal") }}
          </button>
          <button
            type="button"
            :aria-pressed="orientation === 'vertical'"
            :class="{ selected: orientation === 'vertical' }"
            @click="chooseOrientation('vertical')"
          >
            {{ t("pipelines.diagram_vertical", "Vertical") }}
          </button>
        </div>
        <UiRelationToolbar
          :aria-label="t('pipelines.diagram_controls', 'Pipeline diagram controls')"
          :zoom-out-label="t('pipelines.diagram_zoom_out', 'Zoom out')"
          :zoom-in-label="t('pipelines.diagram_zoom_in', 'Zoom in')"
          :fit-label="t('pipelines.diagram_fit', 'Fit diagram')"
          :reset-label="t('pipelines.diagram_reset_layout', 'Reset layout')"
          @zoom-out="viewport?.zoomBy(1 / 1.15)"
          @zoom-in="viewport?.zoomBy(1.15)"
          @fit="fitView"
          @reset="resetLayout"
        />
      </div>
    </header>

    <div v-if="diagram.nodes.length" class="diagram-layout">
      <UiRelationViewport
        ref="viewport"
        class="diagram-viewport"
        :style="{ height: `${viewportHeight}px` }"
        :aria-label="title"
        :help-text="
          t(
            'pipelines.diagram_help',
            'Drag the background to pan. Drag a stage to reposition it. Arrow keys pan, plus and minus zoom, and 0 resets the view. Hold Alt and use an arrow key to move a focused stage.',
          )
        "
        :resize-label="t('pipelines.diagram_resize', 'Resize pipeline diagram')"
        :initial-center="{ x: diagram.width / 2, y: diagram.height / 2 }"
        :content-bounds="contentBounds"
        :content-width="diagram.width"
        :content-height="diagram.height"
        resize-axis="vertical"
      >
        <template #default="{ zoom }">
          <svg
            class="diagram-edges"
            :viewBox="`0 0 ${diagram.width} ${diagram.height}`"
            aria-hidden="true"
          >
            <defs>
              <marker
                :id="arrowMarkerId"
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
              v-for="edge in edges"
              :key="edge.id"
              :d="edge.path"
              :data-kind="edge.kind"
              :data-traversed="edge.traversed ? 'true' : 'false'"
              :marker-end="`url(#${arrowMarkerId})`"
            />
          </svg>
          <template v-for="node in nodes" :key="node.id">
            <UiRelationNodeShell
              class="diagram-node"
              :class="{ selected: selected?.id === node.id }"
              :node-id="node.id"
              :x="node.x"
              :y="node.y"
              :zoom="zoom"
              :aria-label="`${node.id}: ${labelFor(node.strategy)}`"
              :aria-pressed="selected?.id === node.id"
              :data-status="node.executionStatus || undefined"
              :data-presence="node.presence"
              :style="{
                width: `${PIPELINE_NODE_WIDTH}px`,
                height: `${PIPELINE_NODE_HEIGHT}px`,
              }"
              @move="moveNode(node.id, $event)"
              @activate="selectedId = node.id"
              @mouseenter="hoveredId = node.id"
              @mouseleave="hoveredId = ''"
              @focus="hoveredId = node.id"
              @blur="hoveredId = ''"
            >
              <span class="node-kicker">
                <span v-if="node.entry">{{ t("pipelines.node_entry", "Entry") }}</span>
                <span>{{ pipelineStageFamilyLabel(familyFor(node.strategy), t) }}</span>
              </span>
              <strong>{{ node.id }}</strong>
              <span>{{ labelFor(node.strategy) }}</span>
            </UiRelationNodeShell>
            <UiTooltipInfobox
              v-if="hoveredId === node.id"
              :title="node.id"
              :description="pipelineStageFamilyLabel(familyFor(node.strategy), t)"
              :rows="infoRows(node)"
              :style="{
                left: `${node.x}px`,
                top: `${node.y}px`,
                transform: 'translateY(calc(-100% - 8px))',
              }"
            />
          </template>
        </template>
      </UiRelationViewport>

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
.pipeline-diagram header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.diagram-control-stack {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}
.diagram-controls {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
}
.diagram-controls button {
  min-height: 32px;
  padding: 5px 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.75rem;
  cursor: pointer;
}
.diagram-controls button.selected {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
  color: var(--text-primary);
  font-weight: 750;
}
.diagram-controls button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.pipeline-diagram header p,
.diagram-empty {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 0.78rem;
  line-height: 1.5;
}
.diagram-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 240px);
  gap: 12px;
  align-items: start;
}
.diagram-viewport {
  width: 100%;
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
  stroke: var(--border-strong);
  stroke-width: 1.5;
}
.diagram-edges path[data-kind="next"] {
  stroke: var(--text-primary);
}
.diagram-edges path[data-kind="on_empty"] {
  stroke: var(--tone-info-border);
  stroke-dasharray: 5 3;
}
.diagram-edges path[data-kind="on_unavailable"] {
  stroke: var(--tone-warn-border);
  stroke-dasharray: 2 3;
}
.diagram-edges path[data-kind="on_timeout"] {
  stroke: var(--tone-danger-border);
  stroke-dasharray: 1 5;
  stroke-linecap: round;
}
.diagram-edges path[data-kind="on_error"] {
  stroke: var(--tone-danger-border);
  stroke-dasharray: 1 3;
}
.diagram-edges path[data-traversed="true"] {
  stroke-width: 2.25;
}
.diagram-edges marker path {
  fill: var(--text-primary);
}
.diagram-node {
  display: grid;
  align-content: center;
  gap: 2px;
  padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  color: var(--text-primary);
  font: inherit;
  text-align: left;
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
  color: var(--text-secondary);
}
.diagram-node.selected {
  border-color: var(--border-interactive);
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: 1px;
}
.diagram-node:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
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
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.inspector-kicker,
.node-inspector dt {
  color: var(--text-secondary);
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
  color: var(--text-secondary);
  font-size: 0.75rem;
}
.diagram-legend li::before {
  display: inline-block;
  width: 18px;
  margin-right: 6px;
  border-top: 2px solid var(--text-primary);
  content: "";
  transform: translateY(-3px);
}
.diagram-legend li[data-kind="on_empty"]::before {
  border-top-style: dashed;
  border-top-color: var(--tone-info-border);
}
.diagram-legend li[data-kind="on_unavailable"]::before {
  border-top-style: dotted;
  border-top-color: var(--tone-warn-border);
}
.diagram-legend li[data-kind="on_timeout"]::before {
  border-top-style: dotted;
  border-top-color: var(--tone-danger-border);
}
.diagram-legend li[data-kind="on_error"]::before {
  border-top-color: var(--tone-danger-border);
}
.diagram-legend li[data-kind="not_reached"]::before,
.diagram-legend li[data-kind="observed_only"]::before {
  border-top-style: dashed;
  border-top-color: var(--text-secondary);
}
@media (max-width: 860px) {
  .pipeline-diagram header {
    flex-direction: column;
  }
  .diagram-control-stack {
    justify-content: flex-start;
  }
  .diagram-layout {
    grid-template-columns: 1fr;
  }
}
</style>
