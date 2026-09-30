<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    x: number;
    y: number;
    label: string;
    width?: number;
    height?: number;
  }>(),
  { width: 114, height: 20 },
);
</script>

<template>
  <g class="ui-relation-edge-label">
    <rect
      :x="x - width / 2"
      :y="y - height / 2"
      :width="width"
      :height="height"
      :rx="height / 2"
    />
    <text :x="x" :y="y + 4" text-anchor="middle">{{ label }}</text>
  </g>
</template>

<style scoped>
.ui-relation-edge-label rect {
  fill: var(--relation-edge-label-bg, var(--surface-overlay));
  stroke: var(--relation-edge-label-border, var(--border-subtle));
}
.ui-relation-edge-label text {
  fill: var(--relation-edge-label-fg, var(--text-secondary));
  font-size: 12px;
  font-weight: 700;
}
</style>
