<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, useId, watch } from "vue";
import UiRelationCardNode from "../relations/UiRelationCardNode.vue";
import UiRelationEdge from "../relations/UiRelationEdge.vue";
import UiRelationNodeShell from "../relations/UiRelationNodeShell.vue";
import UiRelationViewport from "../relations/UiRelationViewport.vue";
import { useRelationLayoutState } from "../../composables/relations/useRelationLayoutState";
import { relationBoundsForPoints } from "../../domain/relations/geometry";
import { RELATION_SURFACE_PRESETS } from "../../domain/relations/presets";
import {
  PIPELINE_NODE_HEIGHT,
  PIPELINE_NODE_WIDTH,
  layoutPipelineDiagram,
  pipelineEdgePath,
  type PipelineDiagramDensity,
  type PipelineDiagramOrientation,
  type PipelineEdgeKind,
} from "../../domain/pipelineGraph";
import {
  pipelineRunStatusLabel,
  pipelineStageFamilyLabel,
  pipelineStrategyLabel,
} from "../../domain/pipelinePresentation";
import { findTerm, pipelinePhaseSequence, termLabel } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineRunTrace,
  PipelineStage,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";
import PipelineStageInspector from "./PipelineStageInspector.vue";
import UiButton from "../ui/UiButton.vue";
import UiMenu, { type UiMenuItem } from "../ui/UiMenu.vue";
import UiTooltipInfobox, { type TooltipInfoboxRow } from "../ui/UiTooltipInfobox.vue";

const props = withDefaults(
  defineProps<{
    stages: PipelineStage[];
    entryStageIds: string[];
    strategies: PipelineStrategy[];
    execution?: PipelineRunTrace | null;
    title: string;
    description: string;
    /** When given, nodes and the phase strip read in workflow terms. */
    vocabulary?: PipelineWorkflowVocabulary;
    /** Controlled selection; when omitted the diagram keeps its own. */
    selectedStageId?: string;
    /** The editor shows its own stage inspector beside the graph. */
    showInspector?: boolean;
    /** Put the stage inspector under the graph, for narrow panes. */
    stackInspector?: boolean;
  }>(),
  { selectedStageId: undefined, showInspector: true, stackInspector: false },
);
const emit = defineEmits<{ "update:selectedStageId": [id: string] }>();

const surfacePreset = RELATION_SURFACE_PRESETS.pipelineDag;
const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const localSelectedId = ref("");
const selectedId = computed({
  get: () => (props.selectedStageId !== undefined ? props.selectedStageId : localSelectedId.value),
  set: (id: string) => {
    localSelectedId.value = id;
    emit("update:selectedStageId", id);
  },
});
const hoveredId = ref("");
const orientation = ref<PipelineDiagramOrientation>("horizontal");
const density = ref<PipelineDiagramDensity>("compact");
const densityOptions: PipelineDiagramDensity[] = ["compact", "standard", "wide"];
const viewport = ref<InstanceType<typeof UiRelationViewport> | null>(null);
const arrowMarkerId = `pipeline-arrow-${useId()}`;
const layoutState = useRelationLayoutState();

const diagram = computed(() =>
  layoutPipelineDiagram(
    props.stages,
    props.entryStageIds,
    props.execution || null,
    orientation.value,
    density.value,
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
const viewportHeight = computed(() => Math.min(620, Math.max(320, diagram.value.height + 40)));

watch(
  diagram,
  (next) => {
    if (props.selectedStageId !== undefined) return;
    if (!next.nodes.some((node) => node.id === localSelectedId.value)) {
      localSelectedId.value = next.nodes[0]?.id || "";
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

function phaseLabelFor(strategyId: string) {
  const term = findTerm(props.vocabulary?.phases, strategyFor(strategyId)?.phase);
  return term ? termLabel(term, t) : "";
}

function effectNoteFor(strategyId: string) {
  const term = findTerm(props.vocabulary?.effect_notes, strategyFor(strategyId)?.effect_note);
  return term ? termLabel(term, t) : "";
}

const phases = computed(() =>
  props.vocabulary
    ? pipelinePhaseSequence(
        { stages: props.stages, entry_stage_ids: props.entryStageIds },
        props.strategies,
      )
        .map((id) => findTerm(props.vocabulary?.phases, id))
        .filter((term) => term !== null)
    : [],
);

function labelFor(strategyId: string) {
  const strategy = strategyFor(strategyId);
  return strategy ? pipelineStrategyLabel(strategy, t) : strategyId;
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
  if (effectNoteFor(node.strategy))
    rows.push({
      label: t("pipelines.scholarly_effect", "Scholarly effect"),
      value: effectNoteFor(node.strategy),
    });
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

const layoutItems = computed<UiMenuItem[]>(() => [
  {
    id: "horizontal",
    label: t("pipelines.diagram_horizontal", "Horizontal"),
    checked: orientation.value === "horizontal",
  },
  {
    id: "vertical",
    label: t("pipelines.diagram_vertical", "Vertical"),
    checked: orientation.value === "vertical",
  },
  ...densityOptions.map((option) => ({
    id: `density:${option}`,
    label: t(
      `pipelines.diagram_spacing_${option}`,
      `${option.charAt(0).toUpperCase()}${option.slice(1)} spacing`,
    ),
    checked: density.value === option,
  })),
  { id: "reset", label: t("pipelines.diagram_reset_layout", "Reset layout") },
]);

function chooseLayout(id: string) {
  if (id === "reset") resetLayout();
  else if (id.startsWith("density:")) chooseDensity(id.slice(8) as PipelineDiagramDensity);
  else chooseOrientation(id as PipelineDiagramOrientation);
}

function chooseDensity(next: PipelineDiagramDensity) {
  if (density.value === next) return;
  density.value = next;
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
      <div
        class="diagram-control-stack"
        role="group"
        :aria-label="t('pipelines.diagram_controls', 'Pipeline diagram controls')"
      >
        <UiButton
          :label="t('pipelines.diagram_fit', 'Fit diagram')"
          size="small"
          variant="ghost"
          @click="fitView"
        />
        <UiButton
          :label="t('pipelines.diagram_zoom_out', 'Zoom out')"
          size="small"
          variant="ghost"
          @click="viewport?.zoomBy(1 / 1.15)"
        />
        <UiButton
          :label="t('pipelines.diagram_zoom_in', 'Zoom in')"
          size="small"
          variant="ghost"
          @click="viewport?.zoomBy(1.15)"
        />
        <UiMenu
          :label="t('pipelines.diagram_layout', 'Layout')"
          :menu-label="t('pipelines.diagram_layout', 'Layout')"
          :items="layoutItems"
          align="end"
          @select="chooseLayout"
        />
      </div>
    </header>

    <ol
      v-if="phases.length"
      class="phase-strip"
      :aria-label="t('pipelines.workflow_phases', 'Workflow phases')"
    >
      <li v-for="(term, index) in phases" :key="`${term.id}-${index}`">
        {{ termLabel(term, t) }}
      </li>
    </ol>

    <div
      v-if="diagram.nodes.length"
      class="diagram-layout"
      :class="{ 'without-inspector': !showInspector, stacked: stackInspector }"
    >
      <UiRelationViewport
        ref="viewport"
        class="diagram-viewport"
        :style="{ height: `${viewportHeight}px` }"
        :accessible-label="title"
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
        :min-zoom="surfacePreset.minZoom"
        :max-zoom="surfacePreset.maxZoom"
        :resize-axis="surfacePreset.resizeAxis"
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
            <UiRelationEdge
              v-for="edge in edges"
              :key="edge.id"
              class="diagram-edge"
              :path="edge.path"
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
              :accessible-label="`${node.id}: ${labelFor(node.strategy)}`"
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
              <UiRelationCardNode>
                <span class="node-kicker">
                  <span v-if="node.entry">{{ t("pipelines.node_entry", "Entry") }}</span>
                  <span>{{
                    phaseLabelFor(node.strategy) ||
                    pipelineStageFamilyLabel(familyFor(node.strategy), t)
                  }}</span>
                </span>
                <strong>{{ node.id }}</strong>
                <span>{{ labelFor(node.strategy) }}</span>
              </UiRelationCardNode>
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

      <PipelineStageInspector
        v-if="selected && showInspector"
        :node="selected"
        :strategy="strategyFor(selected.strategy)"
        :vocabulary="vocabulary"
        :has-execution="Boolean(execution)"
      />
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
.phase-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.75rem;
}
.phase-strip li {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 700;
}
.phase-strip li + li::before {
  color: var(--text-tertiary);
  content: "→" / "";
}
.pipeline-diagram header h4 {
  margin: 0;
  font-size: 1rem;
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
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-1);
}
.pipeline-diagram header p,
.diagram-empty {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.diagram-layout.without-inspector,
.diagram-layout.stacked {
  grid-template-columns: minmax(0, 1fr);
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
.diagram-edge {
  --relation-edge-stroke: var(--border-strong);
  --relation-edge-opacity: 1;
}
.diagram-edge[data-kind="next"] {
  --relation-edge-stroke: var(--text-primary);
}
.diagram-edge[data-kind="on_empty"] {
  --relation-edge-stroke: var(--tone-info-border);
  stroke-dasharray: 5 3;
}
.diagram-edge[data-kind="on_unavailable"] {
  --relation-edge-stroke: var(--viz-cat-4);
  stroke-dasharray: 9 3 2 3;
}
.diagram-edge[data-kind="on_timeout"] {
  --relation-edge-stroke: var(--tone-danger-border);
  stroke-dasharray: 1 6;
  stroke-linecap: round;
}
.diagram-edge[data-kind="on_error"] {
  --relation-edge-stroke: var(--tone-danger-border);
  stroke-dasharray: 1 3;
}
.diagram-edge[data-traversed="true"] {
  stroke-width: 2.25;
}
.diagram-edges marker path {
  fill: var(--text-primary);
}
.diagram-node {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  --relation-node-border: var(--border-subtle);
  --relation-node-bg: var(--surface-card);
  --relation-node-detail-fg: var(--text-secondary);
  --relation-node-detail-size: 0.75rem;
  --relation-node-kicker-fg: var(--text-secondary);
  --relation-node-kicker-size: 0.75rem;
  --relation-node-title-size: 0.75rem;
}
.diagram-node :deep(.ui-relation-card-node span),
.diagram-node :deep(.ui-relation-card-node strong) {
  white-space: nowrap;
}
.diagram-node.selected {
  --relation-node-border: var(--border-interactive);
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: 1px;
}
.diagram-node:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.diagram-node[data-status="completed"] {
  --relation-node-bg: var(--tone-ok-bg);
  --relation-node-border: var(--tone-ok-border);
}
.diagram-node[data-status="failed"],
.diagram-node[data-status="timed_out"] {
  --relation-node-bg: var(--tone-danger-bg);
  --relation-node-border: var(--tone-danger-border);
}
.diagram-node[data-status="unavailable"],
.diagram-node[data-status="skipped"] {
  --relation-node-bg: var(--tone-warn-bg);
  --relation-node-border: var(--tone-warn-border);
}
.diagram-node[data-presence="not_reached"] {
  opacity: 0.72;
}
.diagram-node[data-presence="observed_only"] {
  --relation-node-border-style: dashed;
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
  border-top-style: dashed;
  border-top-color: var(--viz-cat-4);
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
