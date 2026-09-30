<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId } from "vue";

/**
 * Accessible, page-level tooltip behavior. The default trigger is the shared
 * information icon. `triggerMode="content"` makes the slotted content itself
 * the focus/click/hover trigger, which is useful for compact status chips where
 * adding a second icon would create unnecessary visual noise.
 *
 * Tooltip content is teleported to the page (or its containing open dialog) so
 * scrolling and clipping panes cannot hide it.
 */
const {
  text,
  label = "",
  placement = "top",
  triggerMode = "icon",
  contentFocusable = true,
} = defineProps<{
  text: string;
  label?: string;
  placement?: "top" | "bottom";
  triggerMode?: "icon" | "content";
  contentFocusable?: boolean;
}>();

const id = `${useId()}-tooltip`;
const open = ref(false);
const trigger = ref<HTMLElement | null>(null);
const bubble = ref<HTMLElement | null>(null);
const target = ref<HTMLElement | string>("body");
const side = ref<"top" | "bottom">(placement);
const position = ref<Record<string, string>>({});
const GAP = 6;
const MARGIN = 8;

function place() {
  const anchorElement = trigger.value;
  const content = bubble.value;
  if (!anchorElement || !content) return;
  const anchor = anchorElement.getBoundingClientRect();
  const box = content.getBoundingClientRect();
  const above = anchor.top - GAP - box.height;
  const below = anchor.bottom + GAP;
  const fitsAbove = above >= MARGIN;
  const fitsBelow = below + box.height <= window.innerHeight - MARGIN;
  side.value =
    placement === "top"
      ? fitsAbove || !fitsBelow
        ? "top"
        : "bottom"
      : fitsBelow || !fitsAbove
        ? "bottom"
        : "top";
  const top = side.value === "top" ? Math.max(MARGIN, above) : below;
  const centre = anchor.left + anchor.width / 2 - box.width / 2;
  const left = Math.min(Math.max(MARGIN, centre), window.innerWidth - box.width - MARGIN);
  position.value = { top: `${Math.round(top)}px`, left: `${Math.round(left)}px` };
}
function show() {
  target.value = trigger.value?.closest<HTMLElement>("dialog[open]") || "body";
  open.value = true;
  void nextTick(place);
  window.addEventListener("scroll", hide, true);
  window.addEventListener("resize", hide);
}
function hide() {
  open.value = false;
  window.removeEventListener("scroll", hide, true);
  window.removeEventListener("resize", hide);
}
function toggle() {
  if (open.value) hide();
  else show();
}
function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && open.value) {
    event.preventDefault();
    event.stopPropagation();
    hide();
  }
}
onBeforeUnmount(hide);
</script>

<template>
  <span
    class="ui-tooltip"
    :data-trigger-mode="triggerMode"
    @mouseenter="show"
    @mouseleave="hide"
    @keydown="onKeydown"
  >
    <button
      v-if="triggerMode === 'icon'"
      ref="trigger"
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
    <span
      v-else
      ref="trigger"
      class="ui-tooltip-anchor"
      :tabindex="contentFocusable ? 0 : undefined"
      :aria-label="label || undefined"
      :aria-describedby="id"
      @focus.capture="show"
      @blur.capture="hide"
      @click="toggle"
    >
      <slot />
    </span>
    <Teleport :to="target">
      <span
        :id="id"
        ref="bubble"
        class="ui-tooltip-content"
        role="tooltip"
        :data-side="side"
        :hidden="!open"
        :style="position"
      >
        {{ text }}
      </span>
    </Teleport>
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
  font-size: 0.75rem;
  font-weight: 800;
  line-height: 1;
}
.ui-tooltip-trigger:hover {
  background: var(--surface-hover, var(--soft));
  color: var(--text, currentColor);
}
.ui-tooltip-anchor {
  display: inline-flex;
  min-inline-size: 0;
  border-radius: inherit;
  cursor: help;
}
.ui-tooltip-trigger:focus-visible,
.ui-tooltip-anchor:focus-visible {
  outline: var(--focus-ring-width, 3px) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset, 2px);
}
.ui-tooltip-content {
  position: fixed;
  z-index: 10000;
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
  pointer-events: none;
}
.ui-tooltip-content[hidden] {
  display: none;
}
@media (forced-colors: active) {
  .ui-tooltip-trigger,
  .ui-tooltip-content {
    border-color: CanvasText;
  }
  .ui-tooltip-trigger:focus-visible,
  .ui-tooltip-anchor:focus-visible {
    outline-color: Highlight;
  }
}
</style>
