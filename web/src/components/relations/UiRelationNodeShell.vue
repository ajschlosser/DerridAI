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
import { computed } from "vue";
import { useRelationNodeDrag } from "../../composables/relations/useRelationNodeDrag";
import type { RelationPoint } from "../../domain/relations/types";

const props = withDefaults(
  defineProps<{
    nodeId: string;
    x: number;
    y: number;
    zoom: number;
    accessibleLabel: string;
    draggable?: boolean;
    locked?: boolean;
    interactive?: boolean;
    nudgeStep?: number;
  }>(),
  {
    draggable: true,
    locked: false,
    interactive: true,
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
  if (!props.interactive || !props.draggable || props.locked) return;
  drag.begin(event, point.value);
}

function onPointerMove(event: PointerEvent) {
  if (!props.interactive || !props.draggable || props.locked) return;
  drag.update(event);
}

function onPointerEnd(event: PointerEvent) {
  if (!props.interactive) return;
  drag.end(event);
}

function onClick(event: MouseEvent) {
  if (!props.interactive || drag.consumeClick(event)) return;
  emit("activate", event);
}

function onKeydown(event: KeyboardEvent) {
  if (!props.interactive || !props.draggable || props.locked) return;
  drag.nudge(event, point.value);
}
</script>

<template>
  <component
    :is="interactive ? 'button' : 'div'"
    :type="interactive ? 'button' : undefined"
    class="ui-relation-node-shell"
    :class="{
      dragging: drag.dragging.value,
      locked,
      interactive,
      inert: !interactive,
    }"
    :style="{ left: `${x}px`, top: `${y}px` }"
    :data-relation-node="interactive ? '' : undefined"
    :data-relation-node-id="nodeId"
    :data-node-id="nodeId"
    :aria-label="interactive ? accessibleLabel : undefined"
    :aria-hidden="interactive ? undefined : 'true'"
    @pointerdown.stop="onPointerDown"
    @pointermove.stop="onPointerMove"
    @pointerup.stop="onPointerEnd"
    @pointercancel.stop="onPointerEnd"
    @click="onClick"
    @keydown="onKeydown"
  >
    <slot />
  </component>
</template>

<style scoped>
.ui-relation-node-shell {
  position: absolute;
  touch-action: none;
  user-select: none;
}
.ui-relation-node-shell.interactive:not(.locked) {
  cursor: grab;
}
.ui-relation-node-shell.interactive.dragging:not(.locked) {
  cursor: grabbing;
}
.ui-relation-node-shell.inert {
  pointer-events: none;
}
</style>
