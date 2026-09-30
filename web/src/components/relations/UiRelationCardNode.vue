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
.ui-relation-card-node :deep(small) {
  color: var(--relation-node-kicker-fg, var(--text-tertiary));
  font-size: var(--relation-node-kicker-size, 12px);
  font-weight: var(--relation-node-kicker-weight, 750);
}
.ui-relation-card-node :deep(strong) {
  color: var(--relation-node-title-fg, var(--text-primary));
  font-size: var(--relation-node-title-size, 12.5px);
  font-weight: var(--relation-node-title-weight, 750);
}
.ui-relation-card-node :deep(span) {
  color: var(--relation-node-detail-fg, var(--text-tertiary));
  font-size: var(--relation-node-detail-size, 12px);
}
@media (forced-colors: active) {
  .ui-relation-card-node {
    border-color: ButtonText;
  }
}
</style>
