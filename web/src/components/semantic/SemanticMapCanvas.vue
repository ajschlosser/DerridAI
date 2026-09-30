<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import UiRelationChipNode from "../relations/UiRelationChipNode.vue";
import UiRelationEdge from "../relations/UiRelationEdge.vue";
import UiRelationNodeShell from "../relations/UiRelationNodeShell.vue";
import UiRelationViewport from "../relations/UiRelationViewport.vue";
import { relationBoundsForPoints } from "../../domain/relations/geometry";
import { RELATION_SURFACE_PRESETS } from "../../domain/relations/presets";
import type { RelationPoint } from "../../domain/relations/types";
import { useI18nStore } from "../../stores/i18n";
import type { SemanticMapGraph, SemanticMapNode } from "../../domain/semanticMap";

type SemanticMapDensity = "compact" | "standard" | "wide";

const props = withDefaults(
  defineProps<{ graph: SemanticMapGraph; density?: SemanticMapDensity }>(),
  { density: "compact" },
);
const emit = defineEmits<{ activate: [node: SemanticMapNode] }>();
const i18n = useI18nStore();

const surfacePreset = RELATION_SURFACE_PRESETS.semanticFree;
const ORIGIN = 520;
const nodes = ref<SemanticMapNode[]>([]);
const viewport = ref<InstanceType<typeof UiRelationViewport> | null>(null);

watch(
  () => props.graph,
  (graph) => {
    nodes.value = graph.nodes.map((node) => ({ ...node }));
  },
  { immediate: true },
);

const densityScale: Record<SemanticMapDensity, number> = {
  compact: 1,
  standard: 1.28,
  wide: 1.68,
};

const renderedNodes = computed(() => {
  const scale = densityScale[props.density];
  const source = nodes.value.map((node) => ({
    ...node,
    x: node.x * scale,
    y: node.y * scale,
  }));
  if (props.density === "compact") return source;

  // Keep the deterministic radial placement, but separate nearby labels in
  // map space so wide mode is readable without manual node movement.
  const separated = source.map((node) => ({ ...node }));
  for (let pass = 0; pass < 8; pass += 1) {
    for (let left = 0; left < separated.length; left += 1) {
      for (let right = left + 1; right < separated.length; right += 1) {
        const a = separated[left];
        const b = separated[right];
        const minX = (Math.max(a.label.length, 8) + Math.max(b.label.length, 8)) * 3.5;
        const minY = 34;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        if (Math.abs(dx) >= minX || Math.abs(dy) >= minY) continue;
        const pushX = (minX - Math.abs(dx)) / 2;
        const pushY = (minY - Math.abs(dy)) / 2;
        if (Math.abs(dx) >= Math.abs(dy)) {
          const direction = dx === 0 ? ((left + right) % 2 ? 1 : -1) : Math.sign(dx);
          a.x -= pushX * direction;
          b.x += pushX * direction;
        } else {
          const direction = dy === 0 ? ((left + right) % 2 ? 1 : -1) : Math.sign(dy);
          a.y -= pushY * direction;
          b.y += pushY * direction;
        }
      }
    }
  }
  return separated;
});

const contentSize = computed(() => ORIGIN * 2 * densityScale[props.density]);

const contentBounds = computed(() =>
  relationBoundsForPoints(
    renderedNodes.value.map((node) => ({
      x: contentSize.value / 2 + node.x,
      y: contentSize.value / 2 + node.y,
    })),
    72,
  ),
);

function screen(id: string) {
  const node = renderedNodes.value.find((item) => item.id === id);
  return { x: contentSize.value / 2 + (node?.x || 0), y: contentSize.value / 2 + (node?.y || 0) };
}

function edgePath(sourceId: string, targetId: string) {
  const source = screen(sourceId);
  const target = screen(targetId);
  return `M ${source.x} ${source.y} L ${target.x} ${target.y}`;
}

function moveNodeTo(id: string, point: RelationPoint) {
  const node = nodes.value.find((item) => item.id === id);
  if (!node) return;
  const scale = densityScale[props.density];
  node.x = (point.x - contentSize.value / 2) / scale;
  node.y = (point.y - contentSize.value / 2) / scale;
}

function zoomBy(factor: number) {
  viewport.value?.zoomBy(factor);
}

function fitView() {
  viewport.value?.fitView(contentBounds.value);
}

function resetView() {
  nodes.value = props.graph.nodes.map((node) => ({ ...node }));
  viewport.value?.resetView();
}

function kindLabel(kind: SemanticMapNode["kind"]) {
  return i18n.t(`semantic_map.kind.${kind}`, kind);
}

defineExpose({ zoomBy, fitView, resetView });
</script>

<template>
  <UiRelationViewport
    v-if="nodes.length"
    ref="viewport"
    class="semantic-map-canvas"
    :accessible-label="i18n.t('semantic_map.title', 'Semantic map')"
    :help-text="
      i18n.t(
        'semantic_map.drag_help',
        'Semantic map. Drag the background to move the map. Drag a term to reposition it. Arrow keys pan, plus and minus zoom, and 0 resets the view. Hold Alt and use an arrow key to move a focused term.',
      )
    "
    :resize-label="i18n.t('semantic_map.resize', 'Resize semantic map')"
    :initial-center="{ x: contentSize / 2, y: contentSize / 2 }"
    :content-bounds="contentBounds"
    :content-width="contentSize"
    :content-height="contentSize"
    :min-zoom="surfacePreset.minZoom"
    :max-zoom="surfacePreset.maxZoom"
    :resize-axis="surfacePreset.resizeAxis"
    layer-marker="data-semantic-map-layer"
  >
    <template #default="{ zoom }">
      <svg
        class="semantic-map-edges"
        aria-hidden="true"
        :viewBox="`0 0 ${contentSize} ${contentSize}`"
        :width="contentSize"
        :height="contentSize"
      >
        <UiRelationEdge
          v-for="edge in graph.edges"
          :key="edge.id"
          :path="edgePath(edge.source, edge.target)"
        />
      </svg>
      <UiRelationNodeShell
        v-for="node in renderedNodes"
        :key="node.id"
        class="semantic-map-node"
        :class="`kind-${node.kind}`"
        :node-id="node.id"
        :x="contentSize / 2 + node.x"
        :y="contentSize / 2 + node.y"
        :zoom="zoom"
        :accessible-label="`${kindLabel(node.kind)}: ${node.label}`"
        @move="moveNodeTo(node.id, $event)"
        @activate="emit('activate', node)"
      >
        <UiRelationChipNode :label="node.label" />
      </UiRelationNodeShell>
    </template>
  </UiRelationViewport>
  <p v-else class="semantic-map-empty">
    {{ i18n.t("semantic_map.empty", "No concepts, topics, or persons are available to map yet.") }}
  </p>
</template>

<style scoped>
.semantic-map-canvas {
  height: 100%;
}
.semantic-map-edges {
  position: absolute;
  inset: 0;
  max-width: none;
  overflow: visible;
}
.semantic-map-node {
  max-width: 220px;
  min-height: 28px;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  font-size: 12px;
  line-height: 1.3;
  transform: translate(-12px, -14px);
}
.semantic-map-node:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: 2px;
}
.semantic-map-node {
  --relation-node-dot: var(--accent-fg);
}
.semantic-map-node.kind-topic {
  --relation-node-dot: var(--tone-info-fg);
}
.semantic-map-node.kind-person {
  --relation-node-dot: var(--tone-ok-fg);
}
.semantic-map-node.kind-record {
  --relation-node-dot: var(--tone-warn-fg);
}
.semantic-map-empty {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
}
</style>
