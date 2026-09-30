<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
export type RelationDensity = "compact" | "standard" | "wide";

withDefaults(
  defineProps<{
    modelValue: RelationDensity;
    accessibleLabel: string;
    labels?: Partial<Record<RelationDensity, string>>;
  }>(),
  { labels: () => ({}) },
);

const emit = defineEmits<{ "update:modelValue": [value: RelationDensity] }>();
const options: RelationDensity[] = ["compact", "standard", "wide"];
</script>

<template>
  <div class="ui-relation-density-controls" role="group" :aria-label="accessibleLabel">
    <button
      v-for="option in options"
      :key="option"
      type="button"
      :aria-pressed="modelValue === option"
      :class="{ selected: modelValue === option }"
      @click="emit('update:modelValue', option)"
    >
      {{ labels[option] || option.charAt(0).toUpperCase() + option.slice(1) }}
    </button>
  </div>
</template>

<style scoped>
.ui-relation-density-controls {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
}
.ui-relation-density-controls button {
  min-height: 32px;
  padding: 5px 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.75rem;
  cursor: pointer;
}
.ui-relation-density-controls button.selected {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
  color: var(--text-primary);
  font-weight: 750;
}
.ui-relation-density-controls button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
</style>
