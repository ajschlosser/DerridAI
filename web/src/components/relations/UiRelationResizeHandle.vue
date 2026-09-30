<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string;
    axis?: "horizontal" | "vertical" | "both";
  }>(),
  { axis: "both" },
);

const emit = defineEmits<{
  pointerdown: [event: PointerEvent];
  pointermove: [event: PointerEvent];
  pointerup: [event: PointerEvent];
  pointercancel: [event: PointerEvent];
  keydown: [event: KeyboardEvent];
}>();
</script>

<template>
  <button
    type="button"
    class="ui-relation-resize-handle"
    :class="`axis-${axis}`"
    data-relation-resize-handle
    :aria-label="label"
    :title="label"
    @pointerdown="emit('pointerdown', $event)"
    @pointermove="emit('pointermove', $event)"
    @pointerup="emit('pointerup', $event)"
    @pointercancel="emit('pointercancel', $event)"
    @keydown="emit('keydown', $event)"
  >
    <span aria-hidden="true"></span>
  </button>
</template>

<style scoped>
.ui-relation-resize-handle {
  position: absolute;
  z-index: 4;
  right: 3px;
  bottom: 3px;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--surface-card) 82%, transparent);
  color: var(--text-tertiary);
  cursor: nwse-resize;
  touch-action: none;
}
.ui-relation-resize-handle.axis-vertical {
  right: 50%;
  width: 42px;
  margin-right: -21px;
  cursor: ns-resize;
}
.ui-relation-resize-handle.axis-horizontal {
  bottom: 50%;
  height: 42px;
  margin-bottom: -21px;
  cursor: ew-resize;
}
.ui-relation-resize-handle span {
  display: block;
  width: 11px;
  height: 11px;
  margin: auto;
  border-right: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  opacity: 0.8;
}
.ui-relation-resize-handle.axis-vertical span {
  width: 14px;
  height: 6px;
  border-right: 0;
}
.ui-relation-resize-handle.axis-horizontal span {
  width: 6px;
  height: 14px;
  border-bottom: 0;
}
.ui-relation-resize-handle:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}
.ui-relation-resize-handle:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
@media (forced-colors: active) {
  .ui-relation-resize-handle {
    border: 1px solid ButtonText;
  }
}
</style>
