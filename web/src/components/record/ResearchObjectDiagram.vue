<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
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

const laneNodes = computed(() => {
  const grouped = Object.fromEntries(laneOrder.map((lane) => [lane, []])) as Record<
    LaneId,
    ResearchObjectNode[]
  >;
  for (const node of props.nodes) grouped[laneForType(node.object_type)].push(node);
  return grouped;
});

const canvasHeight = computed(() => {
  const maxLane = Math.max(...laneOrder.map((lane) => laneNodes.value[lane].length), 1);
  return Math.max(300, topOffset + maxLane * (nodeHeight + nodeGap) + 24);
});

const positionedNodes = computed<PositionedNode[]>(() => {
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
  const text = String(value || "").replace(/\s+/g, " ").trim();
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
</script>

<template>
  <div
    class="research-object-diagram"
    role="group"
    :aria-label="ariaLabel || i18n.t('traceability.diagram_label', 'Relationship diagram')"
  >
    <div class="diagram-scroll" tabindex="0">
      <svg
        class="diagram-canvas"
        :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
        :width="canvasWidth"
        :height="canvasHeight"
        role="img"
        :aria-label="i18n.t('traceability.diagram_help', 'Objects are grouped from source material through research output. Select a node to inspect its direct relationships.')"
      >
        <g class="diagram-lanes" aria-hidden="true">
          <g v-for="(lane, index) in laneOrder" :key="lane">
            <rect
              :x="12 + index * (laneWidth + laneGap)"
              y="8"
              :width="laneWidth"
              :height="canvasHeight - 16"
              rx="10"
            />
            <text
              :x="24 + index * (laneWidth + laneGap)"
              y="31"
              class="diagram-lane-label"
            >
              {{ laneLabels[lane] }}
            </text>
          </g>
        </g>

        <g class="diagram-edges" aria-hidden="true">
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

        <g v-for="node in positionedNodes" :key="node.id">
          <foreignObject :x="node.x" :y="node.y" :width="nodeWidth" :height="nodeHeight">
            <button
              xmlns="http://www.w3.org/1999/xhtml"
              type="button"
              class="diagram-node"
              :class="`state-${nodeState(node)}`"
              :data-object-id="node.id"
              :aria-pressed="node.id === focusId"
              @click="emit('focus', node.id)"
            >
              <small>{{ typeLabel(node.object_type) }}</small>
              <strong>{{ truncate(node.label, 30) }}</strong>
              <span v-if="node.summary">{{ truncate(node.summary, 34) }}</span>
            </button>
          </foreignObject>
        </g>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.research-object-diagram {
  min-width: 0;
}
.diagram-scroll {
  max-width: 100%;
  overflow: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-inset);
  overscroll-behavior: contain;
}
.diagram-scroll:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.diagram-canvas {
  display: block;
  max-width: none;
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
  font-size: 10.5px;
  font-weight: 700;
}
.diagram-node {
  width: 100%;
  height: 100%;
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
  cursor: pointer;
}
.diagram-node:hover {
  border-color: var(--border-interactive);
  background: var(--surface-hover);
}
.diagram-node:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: -3px;
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
  font-size: 11px;
  font-weight: 750;
}
.diagram-node strong {
  color: var(--text-primary);
  font-size: 12.5px;
  font-weight: 750;
}
.diagram-node span {
  color: var(--text-tertiary);
  font-size: 11px;
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
</style>
