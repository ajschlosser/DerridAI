<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import UiRelationNodeShell from "../relations/UiRelationNodeShell.vue";
import UiRelationViewport from "../relations/UiRelationViewport.vue";
import { relationBoundsForPoints } from "../../domain/relations/geometry";
import type { RelationPoint } from "../../domain/relations/types";
import { useI18nStore } from "../../stores/i18n";
import type { SemanticMapGraph, SemanticMapNode } from "../../domain/semanticMap";

const props = defineProps<{ graph: SemanticMapGraph }>();
const i18n = useI18nStore();

const ORIGIN = 520;
const CONTENT_SIZE = ORIGIN * 2;
const nodes = ref<SemanticMapNode[]>([]);
const viewport = ref<InstanceType<typeof UiRelationViewport> | null>(null);

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

const contentBounds = computed(() =>
  relationBoundsForPoints(
    nodes.value.map((node) => ({ x: ORIGIN + node.x, y: ORIGIN + node.y })),
    72,
  ),
);

function screen(id: string) {
  const node = positioned.value.byId.get(id);
  return { x: ORIGIN + (node?.x || 0), y: ORIGIN + (node?.y || 0) };
}

function moveNodeTo(id: string, point: RelationPoint) {
  const node = nodes.value.find((item) => item.id === id);
  if (!node) return;
  node.x = point.x - ORIGIN;
  node.y = point.y - ORIGIN;
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
    :aria-label="i18n.t('semantic_map.title', 'Semantic map')"
    :help-text="
      i18n.t(
        'semantic_map.drag_help',
        'Semantic map. Drag the background to move the map. Drag a term to reposition it. Arrow keys pan, plus and minus zoom, and 0 resets the view. Hold Alt and use an arrow key to move a focused term.',
      )
    "
    :resize-label="i18n.t('semantic_map.resize', 'Resize semantic map')"
    :initial-center="{ x: ORIGIN, y: ORIGIN }"
    :content-bounds="contentBounds"
    :content-width="CONTENT_SIZE"
    :content-height="CONTENT_SIZE"
    :max-zoom="2.6"
    resize-axis="vertical"
    layer-marker="data-semantic-map-layer"
  >
    <template #default="{ zoom }">
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
      <UiRelationNodeShell
        v-for="node in nodes"
        :key="node.id"
        class="semantic-map-node"
        :class="`kind-${node.kind}`"
        :node-id="node.id"
        :x="ORIGIN + node.x"
        :y="ORIGIN + node.y"
        :zoom="zoom"
        :aria-label="`${kindLabel(node.kind)}: ${node.label}`"
        @move="moveNodeTo(node.id, $event)"
      >
        <span class="semantic-map-dot" aria-hidden="true"></span>
        <span class="semantic-map-label">{{ node.label }}</span>
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
  width: 1040px;
  height: 1040px;
  overflow: visible;
}
.semantic-map-edges line {
  stroke: var(--border-strong);
  stroke-width: 1.5;
}
.semantic-map-node {
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
  transform: translate(-12px, -14px);
}
.semantic-map-node:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
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
