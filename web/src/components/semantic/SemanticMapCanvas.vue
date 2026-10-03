<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
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
  defineProps<{
    graph: SemanticMapGraph;
    density?: SemanticMapDensity;
    selectedId?: string;
  }>(),
  { density: "compact", selectedId: "" },
);
const emit = defineEmits<{ activate: [node: SemanticMapNode] }>();
const i18n = useI18nStore();

const surfacePreset = RELATION_SURFACE_PRESETS.semanticFree;
const nodes = ref<SemanticMapNode[]>([]);
const viewport = ref<InstanceType<typeof UiRelationViewport> | null>(null);
const userInteracted = ref(false);
let resizeObserver: ResizeObserver | null = null;

const densityScale: Record<SemanticMapDensity, number> = {
  compact: 1,
  standard: 1.12,
  wide: 1.25,
};

const MIN_SCREEN_TARGET = 24;

function targetSizeForZoom(zoom: number) {
  const safeZoom = Number.isFinite(zoom) && zoom > 0 ? zoom : 1;
  return Math.max(MIN_SCREEN_TARGET, MIN_SCREEN_TARGET / safeZoom);
}

function isDecluttered(node: SemanticMapNode, zoom: number) {
  return zoom < 0.58 && node.weight <= 1 && node.kind !== "record" && node.id !== props.selectedId;
}

function densityAdjusted(source: readonly SemanticMapNode[]): SemanticMapNode[] {
  const scale = densityScale[props.density];
  if (scale === 1) return source.map((node) => ({ ...node }));
  const groups = new Map<number, SemanticMapNode[]>();
  source.forEach((node) => {
    const group = groups.get(node.component) || [];
    group.push(node);
    groups.set(node.component, group);
  });
  const centers = new Map<number, RelationPoint>();
  groups.forEach((group, component) => {
    centers.set(component, {
      x: group.reduce((sum, node) => sum + node.x, 0) / Math.max(1, group.length),
      y: group.reduce((sum, node) => sum + node.y, 0) / Math.max(1, group.length),
    });
  });
  return source.map((node) => {
    const center = centers.get(node.component) || { x: 0, y: 0 };
    return {
      ...node,
      x: center.x + (node.x - center.x) * scale,
      y: center.y + (node.y - center.y) * scale,
    };
  });
}

const baseLayoutNodes = computed(() => densityAdjusted(props.graph.nodes));

const frame = computed(() => {
  const bounds = relationBoundsForPoints(
    baseLayoutNodes.value.map((node) => ({ x: node.x, y: node.y })),
    128,
  ) || { x: -320, y: -210, width: 640, height: 420 };
  return {
    width: Math.max(320, bounds.width),
    height: Math.max(240, bounds.height),
    origin: { x: -bounds.x, y: -bounds.y },
  };
});

const contentBounds = computed(() => ({
  x: 0,
  y: 0,
  width: frame.value.width,
  height: frame.value.height,
}));

const relatedIds = computed(() => {
  const related = new Set<string>();
  if (!props.selectedId) return related;
  related.add(props.selectedId);
  for (const edge of props.graph.edges) {
    if (edge.source === props.selectedId) related.add(edge.target);
    if (edge.target === props.selectedId) related.add(edge.source);
  }
  return related;
});

function screen(id: string) {
  const node = nodes.value.find((item) => item.id === id);
  return {
    x: frame.value.origin.x + (node?.x || 0),
    y: frame.value.origin.y + (node?.y || 0),
  };
}

function edgePath(sourceId: string, targetId: string) {
  const source = screen(sourceId);
  const target = screen(targetId);
  return `M ${source.x} ${source.y} L ${target.x} ${target.y}`;
}

function edgeWidth(weight: number) {
  return Math.min(4, 1.1 + Math.log2(Math.max(1, weight) + 1) * 0.72);
}

function moveNodeTo(id: string, point: RelationPoint) {
  const node = nodes.value.find((item) => item.id === id);
  if (!node) return;
  node.x = point.x - frame.value.origin.x;
  node.y = point.y - frame.value.origin.y;
}

function markUserInteraction() {
  userInteracted.value = true;
}

function zoomBy(factor: number) {
  userInteracted.value = true;
  viewport.value?.zoomBy(factor);
}

function fitView() {
  userInteracted.value = false;
  viewport.value?.fitView(contentBounds.value);
}

function resetView() {
  nodes.value = densityAdjusted(props.graph.nodes);
  userInteracted.value = false;
  void nextTick(() => viewport.value?.fitView(contentBounds.value));
}

function centerNode(id: string) {
  const node = nodes.value.find((item) => item.id === id);
  if (!node) return;
  userInteracted.value = true;
  viewport.value?.centerOn(
    {
      x: frame.value.origin.x + node.x,
      y: frame.value.origin.y + node.y,
    },
    1,
  );
}

function scheduleAutomaticFit() {
  void nextTick(() => {
    if (!userInteracted.value && nodes.value.length) viewport.value?.fitView(contentBounds.value);
  });
}

watch(
  () => [props.graph, props.density] as const,
  () => {
    nodes.value = densityAdjusted(props.graph.nodes);
    userInteracted.value = false;
    scheduleAutomaticFit();
  },
  { immediate: true },
);

function kindLabel(kind: SemanticMapNode["kind"]) {
  return i18n.t(`semantic_map.kind.${kind}`, kind);
}

onMounted(() => {
  scheduleAutomaticFit();
  const element = viewport.value?.$el as HTMLElement | undefined;
  if (typeof ResizeObserver !== "undefined" && element) {
    resizeObserver = new ResizeObserver(() => scheduleAutomaticFit());
    resizeObserver.observe(element);
  }
});

onBeforeUnmount(() => resizeObserver?.disconnect());

defineExpose({ zoomBy, fitView, resetView, centerNode });
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
        'Semantic map. Drag the background to move the map. Select a term to inspect its relationships. Drag a term to reposition it. Arrow keys pan, plus and minus zoom, and 0 resets the view. Hold Alt and use an arrow key to move a focused term.',
      )
    "
    :resize-label="i18n.t('semantic_map.resize', 'Resize semantic map')"
    :initial-center="{ x: frame.width / 2, y: frame.height / 2 }"
    :content-bounds="contentBounds"
    :content-width="frame.width"
    :content-height="frame.height"
    :min-zoom="surfacePreset.minZoom"
    :max-zoom="surfacePreset.maxZoom"
    :resize-axis="surfacePreset.resizeAxis"
    layer-marker="data-semantic-map-layer"
    @pointerdown.capture="markUserInteraction"
    @wheel.capture="markUserInteraction"
    @keydown.capture="markUserInteraction"
  >
    <template #default="{ zoom }">
      <svg
        class="semantic-map-edges"
        aria-hidden="true"
        :viewBox="`0 0 ${frame.width} ${frame.height}`"
        :width="frame.width"
        :height="frame.height"
      >
        <UiRelationEdge
          v-for="edge in graph.edges"
          :key="edge.id"
          class="semantic-map-edge"
          :class="{
            dimmed: selectedId && edge.source !== selectedId && edge.target !== selectedId,
          }"
          :path="edgePath(edge.source, edge.target)"
          :width="edgeWidth(edge.weight)"
        />
      </svg>
      <UiRelationNodeShell
        v-for="node in nodes"
        :key="node.id"
        class="semantic-map-node"
        :class="[
          `kind-${node.kind}`,
          {
            selected: node.id === selectedId,
            related: selectedId && relatedIds.has(node.id) && node.id !== selectedId,
            dimmed: selectedId && !relatedIds.has(node.id),
            decluttered: isDecluttered(node, zoom),
          },
        ]"
        :node-id="node.id"
        :x="frame.origin.x + node.x"
        :y="frame.origin.y + node.y"
        :zoom="zoom"
        :accessible-label="`${kindLabel(node.kind)}: ${node.label}`"
        :interactive="!isDecluttered(node, zoom)"
        :style="{ '--semantic-map-target-size': `${targetSizeForZoom(zoom)}px` }"
        @move="moveNodeTo(node.id, $event)"
        @activate="emit('activate', node)"
      >
        <UiRelationChipNode :label="node.label" />
      </UiRelationNodeShell>
    </template>
  </UiRelationViewport>
  <p v-else class="semantic-map-empty">
    {{
      i18n.t(
        "semantic_map.empty",
        "No concepts, topics, persons, or Records are available to map yet.",
      )
    }}
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
.semantic-map-edge {
  transition: opacity 120ms ease;
}
.semantic-map-edge.dimmed {
  opacity: 0.14;
}
.semantic-map-node {
  width: var(--semantic-map-target-size, 24px);
  height: var(--semantic-map-target-size, 28px);
  max-width: none;
  min-height: 0;
  margin: 0;
  padding: 0;
  overflow: visible;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  font-size: 12px;
  line-height: 1.3;
  transform: translate(-50%, -50%);
  transition: opacity 120ms ease;
}
.semantic-map-node :deep(.ui-relation-chip-node) {
  position: absolute;
  top: 50%;
  left: 50%;
  width: max-content;
  max-width: 220px;
  transform: translate(-9px, -50%);
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
.semantic-map-node.selected {
  --relation-node-border: var(--border-interactive);
  --relation-node-shadow: 0 0 0 2px var(--surface-selected);
  z-index: 3;
}
.semantic-map-node.related {
  z-index: 2;
}
.semantic-map-node.dimmed {
  opacity: 0.28;
}
.semantic-map-node.decluttered :deep(.ui-relation-chip-label) {
  display: none;
}
.semantic-map-node.decluttered :deep(.ui-relation-chip-node) {
  padding-inline-end: 2px;
  border-color: transparent;
  background: transparent;
}
.semantic-map-empty {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
}
@media (prefers-reduced-motion: reduce) {
  .semantic-map-edge,
  .semantic-map-node {
    transition: none;
  }
}
</style>
