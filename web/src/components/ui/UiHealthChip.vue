<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    available?: boolean;
    label: string;
    detail?: string;
  }>(),
  { available: false, detail: "" },
);
</script>
<template>
  <span class="ui-health-chip" :data-available="available ? 'true' : 'false'" :title="detail">
    <span class="ui-health-dot" aria-hidden="true"></span>
    <span>{{ label }}</span>
    <span v-if="detail" class="sr-only"> — {{ detail }}</span>
  </span>
</template>
<style scoped>
.ui-health-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 4px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-inset);
  color: var(--text-primary);
  font-size: 0.8125rem;
  font-weight: 700;
}
.ui-health-dot {
  inline-size: 8px;
  block-size: 8px;
  border-radius: 50%;
  background: var(--tone-danger-fg);
}
.ui-health-chip[data-available="true"] {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
  color: var(--accent-fg);
}
.ui-health-chip[data-available="true"] .ui-health-dot {
  background: var(--accent);
}
</style>
