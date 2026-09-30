<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    compact?: boolean;
  }>(),
  { compact: false },
);
</script>

<template>
  <span class="ui-relation-card-node" :class="{ compact }">
    <slot />
  </span>
</template>

<style scoped>
.ui-relation-card-node {
  width: 100%;
  height: 100%;
  display: grid;
  align-content: center;
  gap: 2px;
  min-width: 0;
  overflow: hidden;
  padding: var(--relation-node-padding, 8px 10px);
  border: 1px solid var(--relation-node-border, var(--border-subtle));
  border-radius: var(--relation-node-radius, var(--radius-card));
  background: var(--relation-node-bg, var(--surface-card));
  color: var(--relation-node-fg, var(--text-primary));
  box-shadow: var(--relation-node-shadow, var(--shadow-card));
  text-align: start;
}
.ui-relation-card-node.compact {
  padding: var(--relation-node-padding-compact, 7px 9px);
}
.ui-relation-card-node :deep(small),
.ui-relation-card-node :deep(strong),
.ui-relation-card-node :deep(span) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
@media (forced-colors: active) {
  .ui-relation-card-node {
    border-color: ButtonText;
  }
}
</style>
