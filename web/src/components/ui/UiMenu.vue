<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId } from "vue";
import AppIcon from "../AppIcon.vue";

export interface UiMenuItem {
  id: string;
  label: string;
  icon?: string;
  /** Present when the item cannot run now: the reason, in words. */
  reason?: string;
  /** When set, the item is a radio choice in this menu. */
  checked?: boolean;
}

const props = withDefaults(
  defineProps<{
    label: string;
    items: UiMenuItem[];
    menuLabel?: string;
    disabled?: boolean;
    placement?: "top" | "bottom";
    align?: "start" | "end";
    icon?: string;
    iconOnly?: boolean;
    caret?: boolean;
    ariaLabel?: string;
  }>(),
  {
    menuLabel: "",
    disabled: false,
    placement: "bottom",
    align: "start",
    icon: "",
    iconOnly: false,
    caret: true,
    ariaLabel: "",
  },
);
const emit = defineEmits<{ select: [id: string] }>();

const open = ref(false);
const root = ref<HTMLElement | null>(null);
const trigger = ref<HTMLButtonElement | null>(null);
const menu = ref<HTMLElement | null>(null);
const menuId = `${useId()}-menu`;
const itemId = (id: string) => `${menuId}-${id}`;
const radio = () => props.items.some((item) => typeof item.checked === "boolean");

function itemButtons(): HTMLButtonElement[] {
  return Array.from(menu.value?.querySelectorAll<HTMLButtonElement>('[role^="menuitem"]') ?? []);
}
function focusItem(index: number) {
  const buttons = itemButtons();
  if (buttons.length) buttons[(index + buttons.length) % buttons.length].focus();
}
function outside(event: Event) {
  if (root.value && !root.value.contains(event.target as Node)) close(false);
}
async function show(at: "first" | "last") {
  if (props.disabled) return;
  open.value = true;
  document.addEventListener("pointerdown", outside, true);
  await nextTick();
  focusItem(at === "first" ? 0 : -1);
}
function close(returnFocus: boolean) {
  if (!open.value) return;
  open.value = false;
  document.removeEventListener("pointerdown", outside, true);
  if (returnFocus) trigger.value?.focus();
}
function toggle() {
  if (open.value) close(true);
  else void show("first");
}
function onTriggerKey(event: KeyboardEvent) {
  if (event.key === "ArrowDown") {
    event.preventDefault();
    void show("first");
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    void show("last");
  }
}
function onMenuKey(event: KeyboardEvent) {
  const buttons = itemButtons();
  const current = buttons.indexOf(document.activeElement as HTMLButtonElement);
  if (event.key === "ArrowDown") focusItem(current + 1);
  else if (event.key === "ArrowUp") focusItem(current - 1);
  else if (event.key === "Home") focusItem(0);
  else if (event.key === "End") focusItem(-1);
  else if (event.key === "Escape") close(true);
  else if (event.key === "Tab") close(false);
  else return;
  if (event.key !== "Tab") event.preventDefault();
}
function choose(item: UiMenuItem) {
  if (item.reason) return;
  close(true);
  emit("select", item.id);
}
onBeforeUnmount(() => document.removeEventListener("pointerdown", outside, true));
</script>

<template>
  <div ref="root" class="ui-menu" :data-placement="placement" :data-align="align">
    <button
      ref="trigger"
      type="button"
      class="ui-menu-trigger"
      :class="{ 'icon-only': iconOnly }"
      aria-haspopup="menu"
      :aria-expanded="open"
      :aria-controls="open ? menuId : undefined"
      :aria-label="iconOnly || ariaLabel ? ariaLabel || label : undefined"
      :title="iconOnly ? ariaLabel || label : undefined"
      :disabled="disabled"
      @click="toggle"
      @keydown="onTriggerKey"
    >
      <AppIcon v-if="icon" :name="icon" aria-hidden="true" />
      <span v-if="!iconOnly" class="ui-menu-label">{{ label }}</span>
      <span v-if="caret" class="ui-menu-caret" aria-hidden="true"></span>
    </button>
    <ul
      v-if="open"
      :id="menuId"
      ref="menu"
      class="ui-menu-list"
      role="menu"
      :aria-label="menuLabel || label"
      @keydown="onMenuKey"
    >
      <li v-for="item in items" :key="item.id" role="none">
        <button
          type="button"
          :role="radio() ? 'menuitemradio' : 'menuitem'"
          class="ui-menu-item"
          :aria-checked="radio() ? item.checked === true : undefined"
          :aria-disabled="item.reason ? 'true' : undefined"
          :aria-describedby="item.reason ? itemId(item.id) : undefined"
          tabindex="-1"
          @click="choose(item)"
        >
          <AppIcon v-if="item.icon" :name="item.icon" aria-hidden="true" />
          <span>{{ item.label }}</span>
          <small v-if="item.reason" :id="itemId(item.id)">{{ item.reason }}</small>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.ui-menu {
  position: relative;
  display: inline-flex;
}
.ui-menu-trigger {
  min-height: var(--control-height);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 8px 12px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface-card);
  color: var(--text-primary);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 700;
  line-height: 1.2;
  cursor: pointer;
}
.ui-menu-trigger:hover:not(:disabled) {
  background: var(--surface-hover);
  border-color: var(--border-interactive);
}
.ui-menu-trigger:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.ui-menu-trigger:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.ui-menu-trigger.icon-only {
  width: var(--control-height);
  padding: 0;
}
.ui-menu-trigger :deep(svg) {
  width: 16px;
  height: 16px;
}
.ui-menu-caret {
  display: inline-block;
  margin-inline-start: 2px;
  inline-size: 0.5rem;
  block-size: 0.5rem;
  border-inline-end: 2px solid currentColor;
  border-block-end: 2px solid currentColor;
  transform: translateY(-2px) rotate(45deg);
}
.ui-menu[data-placement="top"] .ui-menu-caret {
  transform: translateY(2px) rotate(-135deg);
}
.ui-menu-list {
  position: absolute;
  z-index: 90;
  inset-inline-start: 0;
  inset-block-start: calc(100% + 6px);
  min-inline-size: 16rem;
  max-inline-size: min(22rem, 86vw);
  margin: 0;
  padding: 6px;
  list-style: none;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-overlay);
  background: var(--surface-overlay);
  box-shadow: var(--shadow-overlay);
}
.ui-menu[data-placement="top"] .ui-menu-list {
  inset-block-start: auto;
  inset-block-end: calc(100% + 6px);
}
.ui-menu[data-align="end"] .ui-menu-list {
  inset-inline-start: auto;
  inset-inline-end: 0;
}
.ui-menu-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
  column-gap: 8px;
  inline-size: 100%;
  min-block-size: 2.5rem;
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 650;
  text-align: start;
  cursor: pointer;
}
.ui-menu-item:has(svg) {
  grid-template-columns: auto minmax(0, 1fr);
}
.ui-menu-item :deep(svg) {
  width: 16px;
  height: 16px;
  margin-top: 2px;
}
.ui-menu-item span,
.ui-menu-item small {
  grid-column: 1 / -1;
}
.ui-menu-item:has(svg) span,
.ui-menu-item:has(svg) small {
  grid-column: 2;
}
.ui-menu-item small {
  font-size: 0.8125rem;
  font-weight: 500;
  line-height: 1.4;
  color: var(--muted);
}
.ui-menu-item:hover,
.ui-menu-item:focus-visible {
  background: var(--surface-hover);
}
.ui-menu-item:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: -3px;
}
.ui-menu-item[aria-disabled="true"] {
  color: var(--muted);
  cursor: not-allowed;
}
.ui-menu-item[aria-checked="true"] {
  background: var(--ui-accent-soft, var(--soft));
  color: var(--accent-fg, var(--text));
}
@media (forced-colors: active) {
  .ui-menu-list {
    border-color: CanvasText;
  }
  .ui-menu-item:focus-visible {
    outline-color: Highlight;
  }
}
</style>
