<script setup lang="ts">
import { ref, useId } from "vue";

const props = withDefaults(
  defineProps<{
    text: string;
    label?: string;
    placement?: "top" | "bottom";
  }>(),
  { label: "", placement: "top" },
);

const id = `${useId()}-tooltip`;
const open = ref(false);

function show() {
  open.value = true;
}
function hide() {
  open.value = false;
}
function toggle() {
  open.value = !open.value;
}
function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    event.preventDefault();
    hide();
  }
}
</script>

<template>
  <span
    class="ui-tooltip"
    :data-placement="placement"
    @mouseenter="show"
    @mouseleave="hide"
    @keydown="onKeydown"
  >
    <button
      type="button"
      class="ui-tooltip-trigger"
      :aria-label="label || text"
      :aria-describedby="id"
      :aria-expanded="open ? 'true' : undefined"
      @focus="show"
      @blur="hide"
      @click="toggle"
    >
      <span aria-hidden="true">i</span>
    </button>
    <span :id="id" class="ui-tooltip-content" role="tooltip" :hidden="!open">
      {{ text }}
    </span>
  </span>
</template>

<style scoped>
.ui-tooltip {
  position: relative;
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
}
.ui-tooltip-trigger {
  display: inline-grid;
  inline-size: 1.75rem;
  block-size: 1.75rem;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--text-tertiary, var(--muted));
  font: inherit;
  cursor: help;
}
.ui-tooltip-trigger > span {
  display: grid;
  inline-size: 1rem;
  block-size: 1rem;
  place-items: center;
  border: 1px solid currentColor;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 800;
  line-height: 1;
}
.ui-tooltip-trigger:hover {
  background: var(--surface-hover, var(--soft));
  color: var(--text, currentColor);
}
.ui-tooltip-trigger:focus-visible {
  outline: var(--focus-ring-width, 3px) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset, 2px);
}
.ui-tooltip-content {
  position: absolute;
  z-index: 100;
  inset-inline-start: 50%;
  inline-size: max-content;
  max-inline-size: min(22rem, calc(100vw - 2rem));
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--border-strong, var(--line-strong));
  border-radius: var(--radius-overlay, 0.625rem);
  background: var(--surface-overlay, var(--card));
  color: var(--text);
  box-shadow: var(--shadow-overlay, 0 12px 30px rgb(0 0 0 / 20%));
  font-size: 0.8125rem;
  font-weight: 500;
  line-height: 1.45;
  text-align: start;
  white-space: normal;
  transform: translateX(-50%);
}
.ui-tooltip[data-placement="top"] .ui-tooltip-content {
  inset-block-end: calc(100% + 0.375rem);
}
.ui-tooltip[data-placement="bottom"] .ui-tooltip-content {
  inset-block-start: calc(100% + 0.375rem);
}
.ui-tooltip-content[hidden] {
  display: none;
}
@media (forced-colors: active) {
  .ui-tooltip-trigger,
  .ui-tooltip-content {
    border-color: CanvasText;
  }
  .ui-tooltip-trigger:focus-visible {
    outline-color: Highlight;
  }
}
</style>
