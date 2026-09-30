<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useRelationNodeDrag } from "../../composables/relations/useRelationNodeDrag";
import type { RelationPoint } from "../../domain/relations/types";

const props = withDefaults(
  defineProps<{
    nodeId: string;
    x: number;
    y: number;
    zoom: number;
    ariaLabel: string;
    draggable?: boolean;
    locked?: boolean;
    nudgeStep?: number;
  }>(),
  {
    draggable: true,
    locked: false,
    nudgeStep: 8,
  },
);

const emit = defineEmits<{
  move: [point: RelationPoint];
  activate: [event: MouseEvent];
}>();

const point = computed(() => ({ x: props.x, y: props.y }));
const drag = useRelationNodeDrag({
  getZoom: () => props.zoom,
  onMove: (next) => emit("move", next),
  nudgeStep: props.nudgeStep,
});

function onPointerDown(event: PointerEvent) {
  if (!props.draggable || props.locked) return;
  drag.begin(event, point.value);
}

function onPointerMove(event: PointerEvent) {
  if (!props.draggable || props.locked) return;
  drag.update(event);
}

function onPointerEnd(event: PointerEvent) {
  drag.end(event);
}

function onClick(event: MouseEvent) {
  if (drag.consumeClick(event)) return;
  emit("activate", event);
}

function onKeydown(event: KeyboardEvent) {
  if (!props.draggable || props.locked) return;
  drag.nudge(event, point.value);
}
</script>

<template>
  <button
    type="button"
    class="ui-relation-node-shell"
    :class="{ dragging: drag.dragging.value, locked }"
    :style="{ left: `${x}px`, top: `${y}px` }"
    data-relation-node
    :data-relation-node-id="nodeId"
    :data-node-id="nodeId"
    :aria-label="ariaLabel"
    @pointerdown.stop="onPointerDown"
    @pointermove.stop="onPointerMove"
    @pointerup.stop="onPointerEnd"
    @pointercancel.stop="onPointerEnd"
    @click="onClick"
    @keydown="onKeydown"
  >
    <slot />
  </button>
</template>

<style scoped>
.ui-relation-node-shell {
  position: absolute;
  touch-action: none;
  user-select: none;
}
.ui-relation-node-shell:not(.locked) {
  cursor: grab;
}
.ui-relation-node-shell.dragging:not(.locked) {
  cursor: grabbing;
}
</style>
