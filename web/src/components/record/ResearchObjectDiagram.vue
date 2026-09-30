<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import UiRelationNodeShell from "../relations/UiRelationNodeShell.vue";
import UiRelationToolbar from "../relations/UiRelationToolbar.vue";
import UiRelationViewport from "../relations/UiRelationViewport.vue";
import { useRelationLayoutState } from "../../composables/relations/useRelationLayoutState";
import { relationBoundsForPoints } from "../../domain/relations/geometry";
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

const canvasWidth = 980;
const laneWidth = 184;
const laneGap = 10;
const nodeWidth = 154;
const nodeHeight = 66;
const nodeGap = 24;
const topOffset = 56;

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
  return Math.max(300, topOffset + maxLane * (nodeHeight + nodeGap) + 24);
});

const automaticNodes = computed<PositionedNode[]>(() => {
  const result: PositionedNode[] = [];
  laneOrder.forEach((lane, laneIndex) => {
    const x = 18 + laneIndex * (laneWidth + laneGap) + (laneWidth - nodeWidth) / 2;
    laneNodes.value[lane].forEach((node, index) => {
      result.push({
        ...node,
        lane,
        x,
        y: topOffset + index * (nodeHeight + nodeGap),
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
    { x: canvasWidth, y: canvasHeight.value },
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
</script>

<template>
  <div
    class="research-object-diagram"
    role="group"
    :aria-label="ariaLabel || i18n.t('traceability.diagram_label', 'Relationship diagram')"
  >
    <div class="diagram-tools">
      <UiRelationToolbar
        :aria-label="i18n.t('traceability.diagram_controls', 'Relationship map controls')"
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
      :aria-label="ariaLabel || i18n.t('traceability.diagram_label', 'Relationship diagram')"
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
      resize-axis="vertical"
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
                :x="12 + index * (laneWidth + laneGap)"
                y="8"
                :width="laneWidth"
                :height="canvasHeight - 16"
                rx="10"
              />
              <text :x="24 + index * (laneWidth + laneGap)" y="31" class="diagram-lane-label">
                {{ laneLabels[lane] }}
              </text>
            </g>
          </g>

          <g class="diagram-edges">
            <template v-for="edge in edges" :key="edge.id">
              <path
                :d="edgePath(edge)"
                class="diagram-edge"
                :class="{
                  active: isActiveEdge(edge),
                  contextual: focusId && !isActiveEdge(edge),
                  application: !edge.normative,
                }"
              />
              <g v-if="isActiveEdge(edge)">
                <rect
                  :x="edgeLabelPosition(edge).x - 57"
                  :y="edgeLabelPosition(edge).y - 10"
                  width="114"
                  height="20"
                  rx="10"
                  class="diagram-edge-label-bg"
                />
                <text
                  :x="edgeLabelPosition(edge).x"
                  :y="edgeLabelPosition(edge).y + 4"
                  text-anchor="middle"
                  class="diagram-edge-label"
                >
                  {{ truncate(relationFromFocus(edge), 24) }}
                </text>
              </g>
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
          :aria-label="`${typeLabel(node.object_type)}: ${node.label}`"
          :aria-pressed="node.id === focusId"
          :data-object-id="node.id"
          :style="{ width: `${nodeWidth}px`, height: `${nodeHeight}px` }"
          @move="moveNode(node.id, $event)"
          @activate="emit('focus', node.id)"
        >
          <small>{{ typeLabel(node.object_type) }}</small>
          <strong>{{ truncate(node.label, 30) }}</strong>
          <span v-if="node.summary">{{ truncate(node.summary, 34) }}</span>
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
  fill: none;
  stroke: var(--border-strong);
  stroke-width: 1.5;
  opacity: 0.72;
}
.diagram-edge.application {
  stroke-dasharray: 5 5;
}
.diagram-edge.active {
  stroke: var(--accent);
  stroke-width: 2.5;
  opacity: 1;
}
.diagram-edge.contextual {
  opacity: 0.22;
}
.diagram-edge-label-bg {
  fill: var(--surface-overlay);
  stroke: var(--border-subtle);
}
.diagram-edge-label {
  fill: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
}
.diagram-node {
  display: grid;
  align-content: center;
  gap: 2px;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-primary);
  padding: 7px 9px;
  text-align: left;
  box-shadow: var(--shadow-card);
}
.diagram-node:hover {
  border-color: var(--border-interactive);
  background: var(--surface-hover);
}
.diagram-node:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.diagram-node.state-focus {
  border-color: var(--accent);
  background: var(--surface-selected);
  box-shadow: var(--elev-2);
}
.diagram-node.state-neighbor {
  border-color: var(--border-interactive);
}
.diagram-node.state-context {
  opacity: 0.48;
}
.diagram-node small,
.diagram-node strong,
.diagram-node span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.diagram-node small {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 750;
}
.diagram-node strong {
  color: var(--text-primary);
  font-size: 12.5px;
  font-weight: 750;
}
.diagram-node span {
  color: var(--text-tertiary);
  font-size: 12px;
}
@media (forced-colors: active) {
  .diagram-edge,
  .diagram-edge.active {
    stroke: CanvasText;
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
