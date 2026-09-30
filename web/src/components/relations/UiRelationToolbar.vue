<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import UiButton from "../ui/UiButton.vue";

withDefaults(
  defineProps<{
    accessibleLabel: string;
    zoomOutLabel: string;
    zoomInLabel: string;
    fitLabel: string;
    resetLabel: string;
    zoomText?: string;
    disabled?: boolean;
  }>(),
  {
    zoomText: "",
    disabled: false,
  },
);

const emit = defineEmits<{
  zoomOut: [];
  zoomIn: [];
  fit: [];
  reset: [];
}>();
</script>

<template>
  <div class="ui-relation-toolbar" role="group" :aria-label="accessibleLabel">
    <slot name="before" />
    <UiButton
      :label="zoomOutLabel"
      size="small"
      variant="ghost"
      :disabled="disabled"
      @click="emit('zoomOut')"
    />
    <span v-if="zoomText" class="ui-relation-toolbar-zoom" aria-live="polite">{{ zoomText }}</span>
    <UiButton
      :label="zoomInLabel"
      size="small"
      variant="ghost"
      :disabled="disabled"
      @click="emit('zoomIn')"
    />
    <UiButton
      :label="fitLabel"
      size="small"
      variant="ghost"
      :disabled="disabled"
      @click="emit('fit')"
    />
    <UiButton
      :label="resetLabel"
      size="small"
      variant="ghost"
      :disabled="disabled"
      @click="emit('reset')"
    />
    <slot name="after" />
  </div>
</template>

<style scoped>
.ui-relation-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}
.ui-relation-toolbar-zoom {
  min-width: 4.5ch;
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
  text-align: center;
}
</style>
