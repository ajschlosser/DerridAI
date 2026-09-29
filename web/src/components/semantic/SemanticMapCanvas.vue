<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18nStore } from "../../stores/i18n";
import {
  clampScale,
  moveNode,
  panBy,
  type SemanticMapGraph,
  type SemanticMapNode,
} from "../../domain/semanticMap";

const props = defineProps<{ graph: SemanticMapGraph }>();
const i18n = useI18nStore();

const ORIGIN = 520;
const pan = ref({ x: 0, y: 0 });
const scale = ref(1);
const nodes = ref<SemanticMapNode[]>([]);
const dragging = ref(false);
const surface = ref<HTMLElement | null>(null);

watch(
  () => props.graph,
  (graph) => {
    nodes.value = graph.nodes.map((node) => ({ ...node }));
  },
  { immediate: true },
);

const positioned = computed(() => {
  const byId = new Map(nodes.value.map((node) => [node.id, node]));
  return { byId };
});

function screen(id: string) {
  const node = positioned.value.byId.get(id);
  return { x: ORIGIN + (node?.x || 0), y: ORIGIN + (node?.y || 0) };
}

let drag: {
  kind: "pan" | "node";
  id: string;
  x: number;
  y: number;
  panX: number;
  panY: number;
  nodeX: number;
  nodeY: number;
} | null = null;

function onPointerDown(event: PointerEvent) {
  if (event.button != null && event.button !== 0) return;
  const surface = event.currentTarget as HTMLElement;
  surface.setPointerCapture?.(event.pointerId);
  const nodeEl = (event.target as Element | null)?.closest?.("[data-node-id]");
  const id = nodeEl?.getAttribute("data-node-id") || "";
  const node = nodes.value.find((item) => item.id === id);
  dragging.value = true;
  drag = {
    kind: node ? "node" : "pan",
    id,
    x: event.clientX,
    y: event.clientY,
    panX: pan.value.x,
    panY: pan.value.y,
    nodeX: node?.x || 0,
    nodeY: node?.y || 0,
  };
}

function onPointerMove(event: PointerEvent) {
  if (!drag) return;
  const delta = { x: event.clientX - drag.x, y: event.clientY - drag.y };
  if (drag.kind === "pan") {
    pan.value = panBy({ x: drag.panX, y: drag.panY }, delta);
    return;
  }
  const node = nodes.value.find((item) => item.id === drag?.id);
  if (!node) return;
  const next = moveNode({ x: drag.nodeX, y: drag.nodeY }, delta, scale.value);
  node.x = next.x;
  node.y = next.y;
}

function endDrag() {
  drag = null;
  dragging.value = false;
}

function zoomBy(factor: number) {
  scale.value = clampScale(scale.value * factor);
}

function center() {
  const box = surface.value?.getBoundingClientRect();
  const width = box?.width || 640;
  const height = box?.height || 420;
  pan.value = { x: width / 2 - ORIGIN, y: height / 2 - ORIGIN };
}

function resetView() {
  scale.value = 1;
  nodes.value = props.graph.nodes.map((node) => ({ ...node }));
  center();
}

onMounted(center);

function onKeydown(event: KeyboardEvent) {
  const step = event.shiftKey ? 96 : 48;
  if (event.key === "ArrowLeft") pan.value = panBy(pan.value, { x: step, y: 0 });
  else if (event.key === "ArrowRight") pan.value = panBy(pan.value, { x: -step, y: 0 });
  else if (event.key === "ArrowUp") pan.value = panBy(pan.value, { x: 0, y: step });
  else if (event.key === "ArrowDown") pan.value = panBy(pan.value, { x: 0, y: -step });
  else if (event.key === "+" || event.key === "=") zoomBy(1.15);
  else if (event.key === "-" || event.key === "_") zoomBy(1 / 1.15);
  else if (event.key === "0") resetView();
  else return;
  event.preventDefault();
}

function kindLabel(kind: SemanticMapNode["kind"]) {
  return i18n.t(`semantic_map.kind.${kind}`, kind);
}

defineExpose({ zoomBy, resetView });
</script>

<template>
  <div
    v-if="nodes.length"
    ref="surface"
    class="semantic-map-canvas"
    :class="{ dragging }"
    role="application"
    tabindex="0"
    :aria-label="
      i18n.t(
        'semantic_map.drag_help',
        'Semantic map. Drag the background to move the map. Drag a term to reposition it. Arrow keys pan, plus and minus zoom, and 0 resets.',
      )
    "
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="endDrag"
    @pointercancel="endDrag"
    @keydown="onKeydown"
  >
    <div
      class="semantic-map-layer"
      data-semantic-map-layer
      :style="{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})` }"
    >
      <svg class="semantic-map-edges" aria-hidden="true">
        <line
          v-for="edge in graph.edges"
          :key="edge.id"
          :x1="screen(edge.source).x"
          :y1="screen(edge.source).y"
          :x2="screen(edge.target).x"
          :y2="screen(edge.target).y"
        />
      </svg>
      <button
        v-for="node in nodes"
        :key="node.id"
        type="button"
        class="semantic-map-node"
        :class="`kind-${node.kind}`"
        :data-node-id="node.id"
        :style="{ left: `${ORIGIN + node.x}px`, top: `${ORIGIN + node.y}px` }"
        :aria-label="`${kindLabel(node.kind)}: ${node.label}`"
      >
        <span class="semantic-map-dot" aria-hidden="true"></span>
        <span class="semantic-map-label">{{ node.label }}</span>
      </button>
    </div>
  </div>
  <p v-else class="semantic-map-empty">
    {{
      i18n.t(
        "semantic_map.empty",
        "No concepts, topics, or persons are available to map yet.",
      )
    }}
  </p>
</template>

<style scoped>
.semantic-map-canvas {
  position: relative;
  min-height: 220px;
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-inset);
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.semantic-map-canvas.dragging {
  cursor: grabbing;
}
.semantic-map-canvas:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-interactive);
  outline-offset: var(--focus-ring-offset);
}
.semantic-map-layer {
  position: absolute;
  inset: 0;
  width: 1040px;
  height: 1040px;
  transform-origin: 0 0;
}
.semantic-map-edges {
  position: absolute;
  inset: 0;
  width: 1040px;
  height: 1040px;
  overflow: visible;
}
.semantic-map-edges line {
  stroke: var(--border-strong);
  stroke-width: 1.5;
}
.semantic-map-node {
  position: absolute;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 220px;
  min-height: 28px;
  margin: 0;
  padding: 2px 8px 2px 2px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-card);
  color: var(--text-primary);
  font: inherit;
  font-size: 12px;
  line-height: 1.3;
  cursor: grab;
  transform: translate(-12px, -14px);
}
.semantic-map-node:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-interactive);
  outline-offset: 2px;
}
.semantic-map-dot {
  width: 12px;
  height: 12px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--accent-fg);
}
.kind-topic .semantic-map-dot {
  background: var(--tone-info-fg);
}
.kind-person .semantic-map-dot {
  background: var(--tone-ok-fg);
}
.kind-record .semantic-map-dot {
  background: var(--tone-warn-fg);
}
.semantic-map-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.semantic-map-empty {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
}
</style>
