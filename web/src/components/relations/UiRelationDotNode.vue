<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    radius: number;
    label: string;
    showLabel?: boolean;
    labelOffset?: number;
  }>(),
  { showLabel: false, labelOffset: 5 },
);
</script>

<template>
  <g class="ui-relation-dot-node">
    <circle class="halo" :r="radius + 5" />
    <circle class="dot" :r="radius" />
    <text v-if="showLabel" class="label" :x="radius + labelOffset" y="4">
      {{ label }}
    </text>
  </g>
</template>

<style scoped>
.ui-relation-dot-node {
  cursor: grab;
  touch-action: none;
}
.halo {
  fill: none;
  stroke: var(--relation-node-halo, transparent);
  stroke-width: 3;
  stroke-opacity: var(--relation-node-halo-opacity, 1);
}
.dot {
  fill: var(--relation-node-dot, var(--hue, var(--accent)));
  fill-opacity: var(--relation-node-dot-opacity, 1);
  stroke: var(--relation-node-dot-border, var(--surface-raised));
  stroke-width: var(--relation-node-dot-border-width, 1.5);
}
.label {
  fill: var(--relation-node-label, var(--text-primary));
  font-size: 12px;
  font-weight: var(--fw-semibold);
  paint-order: stroke;
  stroke: var(--relation-node-label-halo, var(--surface-raised));
  stroke-width: 3px;
  stroke-linejoin: round;
  pointer-events: none;
}
</style>
