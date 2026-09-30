<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
defineProps<{
  label: string;
}>();
</script>

<template>
  <span class="ui-relation-chip-node">
    <span class="ui-relation-chip-dot" aria-hidden="true"><slot name="dot" /></span>
    <span class="ui-relation-chip-label">{{ label }}</span>
  </span>
</template>

<style scoped>
.ui-relation-chip-node {
  display: inline-flex;
  max-width: 100%;
  min-width: 0;
  align-items: center;
  gap: 6px;
  padding: 2px 8px 2px 2px;
  border: 1px solid var(--relation-node-border, var(--border-subtle));
  border-radius: var(--radius-pill);
  background: var(--relation-node-bg, var(--surface-card));
  color: var(--relation-node-fg, var(--text-primary));
  box-shadow: var(--relation-node-shadow, none);
}
.ui-relation-chip-dot {
  width: 12px;
  height: 12px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--relation-node-dot, var(--accent-fg));
}
.ui-relation-chip-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (forced-colors: active) {
  .ui-relation-chip-node {
    border-color: ButtonText;
  }
  .ui-relation-chip-dot {
    border: 1px solid ButtonText;
    background: ButtonFace;
  }
}
</style>
