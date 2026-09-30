<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import UiRelationCardNode from "../relations/UiRelationCardNode.vue";
import UiRelationEdge from "../relations/UiRelationEdge.vue";
import UiRelationEdgeLabel from "../relations/UiRelationEdgeLabel.vue";
import UiRelationNodeShell from "../relations/UiRelationNodeShell.vue";
import UiRelationToolbar from "../relations/UiRelationToolbar.vue";
import UiRelationDensityControls, {
  type RelationDensity,
} from "../relations/UiRelationDensityControls.vue";
import UiRelationViewport from "../relations/UiRelationViewport.vue";
import { useRelationLayoutState } from "../../composables/relations/useRelationLayoutState";
import { relationBoundsForPoints } from "../../domain/relations/geometry";
import { RELATION_SURFACE_PRESETS } from "../../domain/relations/presets";
import { useI18nStore } from "../../stores/i18n";
import type { ResearchObjectEdge, ResearchObjectNode } from "../../types/researchObjectGraph";

const props = withDefaults(
  defineProps<{
    nodes: ResearchObjectNode[];
    edges: ResearchObjectEdge[];
    focusId?: string;
    ariaLabel?: string;
  }>(),
  { focusId: "", ariaLabel: "" },
);
const emit = defineEmits<{ focus: [id: string] }>();
const i18n = useI18nStore();
const viewport = ref<InstanceType<typeof UiRelationViewport> | null>(null);
const layoutState = useRelationLayoutState();

const surfacePreset = RELATION_SURFACE_PRESETS.provenanceLanes;

type LaneId = "source" | "record" | "metadata" | "evidence" | "research";
type PositionedNode = ResearchObjectNode & { x: number; y: number; lane: LaneId };

const laneOrder: LaneId[] = ["source", "record", "metadata", "evidence", "research"];
const laneTypes: Record<LaneId, Set<string>> = {
  source: new Set(["SourceDocument", "SourceSpan", "CorpusPublication"]),
  record: new Set(["Record", "RecordRevision"]),
  metadata: new Set(["FieldAssertion"]),
  evidence: new Set(["RetrievalRun", "EvidenceRef", "EvidencePacket"]),
  research: new Set(["SupportBinding", "GenerationRun", "GeneratedClaim", "ResearchRun"]),
};
const laneLabels = computed<Record<LaneId, string>>(() => ({
  source: i18n.t("traceability.lane_source", "Source"),
  record: i18n.t("traceability.lane_record", "Record"),
  metadata: i18n.t("traceability.lane_metadata", "Metadata & review"),
  evidence: i18n.t("traceability.lane_evidence", "Evidence"),
  research: i18n.t("traceability.lane_research", "Research output"),
}));

const nodeWidth = 154;
const nodeHeight = 66;
const topOffset = 56;
const density = ref<RelationDensity>("compact");
const densitySpacing: Record<
  RelationDensity,
  { canvasWidth: number; laneWidth: number; laneGap: number; nodeGap: number }
> = {
  compact: { canvasWidth: 980, laneWidth: 184, laneGap: 10, nodeGap: 24 },
  standard: { canvasWidth: 1160, laneWidth: 210, laneGap: 26, nodeGap: 42 },
  wide: { canvasWidth: 1420, laneWidth: 250, laneGap: 48, nodeGap: 68 },
};
const spacing = computed(() => densitySpacing[density.value]);
const canvasWidth = computed(() => spacing.value.canvasWidth);

function laneForType(type: string): LaneId {
  return laneOrder.find((lane) => laneTypes[lane].has(type)) || "research";
}

const laneNodes = computed<Record<LaneId, ResearchObjectNode[]>>(() => {
  const grouped: Record<LaneId, ResearchObjectNode[]> = {
    source: [],
    record: [],
    metadata: [],
    evidence: [],
    research: [],
  };
  for (const node of props.nodes) grouped[laneForType(node.object_type)].push(node);
  return grouped;
});

const canvasHeight = computed(() => {
  const maxLane = Math.max(...laneOrder.map((lane) => laneNodes.value[lane].length), 1);
  return Math.max(300, topOffset + maxLane * (nodeHeight + spacing.value.nodeGap) + 24);
});

const automaticNodes = computed<PositionedNode[]>(() => {
  const result: PositionedNode[] = [];
  laneOrder.forEach((lane, laneIndex) => {
    const x =
      18 +
      laneIndex * (spacing.value.laneWidth + spacing.value.laneGap) +
      (spacing.value.laneWidth - nodeWidth) / 2;
    laneNodes.value[lane].forEach((node, index) => {
      result.push({
        ...node,
        lane,
        x,
        y: topOffset + index * (nodeHeight + spacing.value.nodeGap),
      });
    });
  });
  return result;
});

const positionedNodes = computed<PositionedNode[]>(() =>
  automaticNodes.value.map((node) => ({
    ...node,
    ...layoutState.positionFor(node.id, { x: node.x, y: node.y }),
  })),
);

const positionMap = computed(() => new Map(positionedNodes.value.map((node) => [node.id, node])));

const connectedIds = computed(() => {
  if (!props.focusId) return new Set<string>();
  const ids = new Set<string>([props.focusId]);
  for (const edge of props.edges) {
    if (edge.source === props.focusId) ids.add(edge.target);
    if (edge.target === props.focusId) ids.add(edge.source);
  }
  return ids;
});

const contentBounds = computed(() => {
  const points = [
    { x: 0, y: 0 },
    { x: canvasWidth.value, y: canvasHeight.value },
    ...positionedNodes.value.flatMap((node) => [
      { x: node.x, y: node.y },
      { x: node.x + nodeWidth, y: node.y + nodeHeight },
    ]),
  ];
  return relationBoundsForPoints(points, 20);
});

const viewportHeight = computed(() => Math.min(680, Math.max(360, canvasHeight.value)));

function edgePath(edge: ResearchObjectEdge) {
  const source = positionMap.value.get(edge.source);
  const target = positionMap.value.get(edge.target);
  if (!source || !target) return "";
  const sx = source.x + nodeWidth / 2;
  const sy = source.y + nodeHeight / 2;
  const tx = target.x + nodeWidth / 2;
  const ty = target.y + nodeHeight / 2;
  if (Math.abs(tx - sx) < 12) {
    const bend = sx + 52;
    return `M ${sx} ${sy} C ${bend} ${sy}, ${bend} ${ty}, ${tx} ${ty}`;
  }
  const mid = sx + (tx - sx) / 2;
  return `M ${sx} ${sy} C ${mid} ${sy}, ${mid} ${ty}, ${tx} ${ty}`;
}

function edgeLabelPosition(edge: ResearchObjectEdge) {
  const source = positionMap.value.get(edge.source);
  const target = positionMap.value.get(edge.target);
  if (!source || !target) return { x: 0, y: 0 };
  return {
    x: (source.x + target.x) / 2 + nodeWidth / 2,
    y: (source.y + target.y) / 2 + nodeHeight / 2 - 7,
  };
}

function relationFromFocus(edge: ResearchObjectEdge) {
  return edge.source === props.focusId ? edge.relation : edge.inverse_relation;
}

function isActiveEdge(edge: ResearchObjectEdge) {
  return edge.source === props.focusId || edge.target === props.focusId;
}

function nodeState(node: ResearchObjectNode) {
  if (!props.focusId) return "normal";
  if (node.id === props.focusId) return "focus";
  if (connectedIds.value.has(node.id)) return "neighbor";
  return "context";
}

function truncate(value: unknown, limit = 32) {
  const text = String(value || "")
    .replace(/\s+/g, " ")
    .trim();
  if (!text) return "";
  return text.length <= limit ? text : `${text.slice(0, limit - 1).trim()}…`;
}

function typeLabel(type: string) {
  const fallback: Record<string, string> = {
    SourceDocument: "Source document",
    SourceSpan: "Source passage",
    Record: "Corpus record",
    RecordRevision: "Record revision",
    FieldAssertion: "Metadata assertion",
    CorpusPublication: "Corpus publication",
    RetrievalRun: "Retrieval run",
    EvidenceRef: "Evidence reference",
    EvidencePacket: "Evidence packet",
    GenerationRun: "Generation run",
    GeneratedClaim: "Generated claim",
    SupportBinding: "Claim support link",
    ResearchRun: "Research run",
  };
  return i18n.t(`traceability.type.${type}`, fallback[type] || type);
}

function moveNode(id: string, point: { x: number; y: number }) {
  layoutState.setPosition(id, point);
}

function fitView() {
  viewport.value?.fitView(contentBounds.value);
}

function resetLayout() {
  layoutState.clearPositions();
  viewport.value?.resetView();
}

function chooseDensity(next: RelationDensity) {
  if (density.value === next) return;
  density.value = next;
  layoutState.clearPositions();
  viewport.value?.fitView(contentBounds.value);
}
</script>

<template>
  <div
    class="research-object-diagram"
    role="group"
    :aria-label="ariaLabel || i18n.t('traceability.diagram_label', 'Relationship diagram')"
  >
    <div class="diagram-tools">
      <UiRelationDensityControls
        :model-value="density"
        :accessible-label="i18n.t('traceability.diagram_density', 'Card spacing')"
        :labels="{
          compact: i18n.t('traceability.diagram_density_compact', 'Compact'),
          standard: i18n.t('traceability.diagram_density_standard', 'Standard'),
          wide: i18n.t('traceability.diagram_density_wide', 'Wide'),
        }"
        @update:model-value="chooseDensity"
      />
      <UiRelationToolbar
        :accessible-label="i18n.t('traceability.diagram_controls', 'Relationship map controls')"
        :zoom-out-label="i18n.t('traceability.diagram_zoom_out', 'Zoom out')"
        :zoom-in-label="i18n.t('traceability.diagram_zoom_in', 'Zoom in')"
        :fit-label="i18n.t('traceability.diagram_fit', 'Fit map')"
        :reset-label="i18n.t('traceability.diagram_reset_layout', 'Reset layout')"
        @zoom-out="viewport?.zoomBy(1 / 1.15)"
        @zoom-in="viewport?.zoomBy(1.15)"
        @fit="fitView"
        @reset="resetLayout"
      />
    </div>

    <UiRelationViewport
      ref="viewport"
      class="diagram-viewport"
      :style="{ height: `${viewportHeight}px` }"
      :accessible-label="ariaLabel || i18n.t('traceability.diagram_label', 'Relationship diagram')"
      :help-text="
        i18n.t(
          'traceability.diagram_help',
          'Objects are grouped from source material through research output. Drag the background to pan, drag a node to reposition it, and select a node to inspect its direct relationships.',
        )
      "
      :resize-label="i18n.t('traceability.diagram_resize', 'Resize relationship map')"
      :initial-center="{ x: canvasWidth / 2, y: canvasHeight / 2 }"
      :content-bounds="contentBounds"
      :content-width="canvasWidth"
      :content-height="canvasHeight"
      :min-zoom="surfacePreset.minZoom"
      :max-zoom="surfacePreset.maxZoom"
      :resize-axis="surfacePreset.resizeAxis"
    >
      <template #default="{ zoom }">
        <svg
          class="diagram-canvas"
          :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
          :width="canvasWidth"
          :height="canvasHeight"
          aria-hidden="true"
        >
          <g class="diagram-lanes">
            <g v-for="(lane, index) in laneOrder" :key="lane">
              <rect
                :x="12 + index * (spacing.laneWidth + spacing.laneGap)"
                y="8"
                :width="spacing.laneWidth"
                :height="canvasHeight - 16"
                rx="10"
              />
              <text
                :x="24 + index * (spacing.laneWidth + spacing.laneGap)"
                y="31"
                class="diagram-lane-label"
              >
                {{ laneLabels[lane] }}
              </text>
            </g>
          </g>

          <g class="diagram-edges">
            <template v-for="edge in edges" :key="edge.id">
              <UiRelationEdge
                :path="edgePath(edge)"
                class="diagram-edge"
                :class="{
                  active: isActiveEdge(edge),
                  contextual: focusId && !isActiveEdge(edge),
                  application: !edge.normative,
                }"
              />
              <UiRelationEdgeLabel
                v-if="isActiveEdge(edge)"
                class="diagram-edge-label"
                :x="edgeLabelPosition(edge).x"
                :y="edgeLabelPosition(edge).y"
                :label="truncate(relationFromFocus(edge), 24)"
              />
            </template>
          </g>
        </svg>

        <UiRelationNodeShell
          v-for="node in positionedNodes"
          :key="node.id"
          class="diagram-node"
          :class="`state-${nodeState(node)}`"
          :node-id="node.id"
          :x="node.x"
          :y="node.y"
          :zoom="zoom"
          :accessible-label="`${typeLabel(node.object_type)}: ${node.label}`"
          :aria-pressed="node.id === focusId"
          :data-object-id="node.id"
          :style="{ width: `${nodeWidth}px`, height: `${nodeHeight}px` }"
          @move="moveNode(node.id, $event)"
          @activate="emit('focus', node.id)"
        >
          <UiRelationCardNode class="diagram-node-card" compact>
            <small>{{ typeLabel(node.object_type) }}</small>
            <strong>{{ truncate(node.label, 30) }}</strong>
            <span v-if="node.summary">{{ truncate(node.summary, 34) }}</span>
          </UiRelationCardNode>
        </UiRelationNodeShell>
      </template>
    </UiRelationViewport>
  </div>
</template>

<style scoped>
.research-object-diagram {
  display: grid;
  gap: 8px;
  min-width: 0;
}
.diagram-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  justify-content: flex-end;
}
.diagram-viewport {
  width: 100%;
}
.diagram-canvas {
  position: absolute;
  inset: 0;
  display: block;
  max-width: none;
  overflow: visible;
  font-family: var(--font-ui);
}
.diagram-lanes rect {
  fill: var(--surface-card);
  stroke: var(--border-subtle);
}
.diagram-lane-label {
  fill: var(--text-tertiary);
  font-size: 12px;
  font-weight: 750;
  letter-spacing: 0.02em;
}
.diagram-edge {
  --relation-edge-stroke: var(--border-strong);
  --relation-edge-opacity: 0.72;
}
.diagram-edge.application {
  stroke-dasharray: 5 5;
}
.diagram-edge.active {
  --relation-edge-stroke: var(--accent);
  --relation-edge-opacity: 1;
  stroke-width: 2.5;
}
.diagram-edge.contextual {
  --relation-edge-opacity: 0.22;
}
.diagram-node {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  text-align: left;
  --relation-node-border: var(--border-strong);
  --relation-node-radius: var(--radius-control);
  --relation-node-bg: var(--surface-card);
  --relation-node-shadow: var(--shadow-card);
}
.diagram-node:hover {
  --relation-node-border: var(--border-interactive);
  --relation-node-bg: var(--surface-hover);
}
.diagram-node:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.diagram-node.state-focus {
  --relation-node-border: var(--accent);
  --relation-node-bg: var(--surface-selected);
  --relation-node-shadow: var(--elev-2);
}
.diagram-node.state-neighbor {
  --relation-node-border: var(--border-interactive);
}
.diagram-node.state-context {
  opacity: 0.48;
}
.diagram-node-card {
  width: 100%;
  height: 100%;
}
@media (forced-colors: active) {
  .diagram-edge,
  .diagram-edge.active {
    --relation-edge-stroke: CanvasText;
  }
  .diagram-node.state-focus {
    outline: 2px solid Highlight;
  }
}
@media (max-width: 620px) {
  .diagram-tools {
    justify-content: flex-start;
  }
}
</style>
