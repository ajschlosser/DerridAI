<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    path: string;
    width?: number;
    title?: string;
  }>(),
  { width: 1.5, title: "" },
);
</script>

<template>
  <path class="ui-relation-edge" :d="path" :stroke-width="width">
    <title v-if="title">{{ title }}</title>
  </path>
</template>

<style scoped>
.ui-relation-edge {
  fill: none;
  stroke: var(--relation-edge-stroke, var(--border-strong));
  opacity: var(--relation-edge-opacity, 0.72);
}
</style>
