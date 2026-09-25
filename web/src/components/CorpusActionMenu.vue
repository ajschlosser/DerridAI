<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId } from "vue";

// A menu button for the secondary actions on a record. An item that cannot run stays in the list and
// stays focusable with the reason it is unavailable shown under it, so a keyboard or screen-reader
// user learns why instead of finding a dead control. Follows the WAI-ARIA menu button pattern:
// Enter, Space and the arrow keys open it, the arrows and Home/End move, Escape closes and returns
// focus, and Tab closes it.
export interface CorpusActionMenuItem {
  id: string;
  label: string;
  /** Present when the item cannot run now: the reason, in words. */
  reason?: string;
}

const props = withDefaults(
  defineProps<{
    label: string;
    items: CorpusActionMenuItem[];
    menuLabel?: string;
    disabled?: boolean;
    placement?: "top" | "bottom";
  }>(),
  { menuLabel: "", disabled: false, placement: "top" },
);
const emit = defineEmits<{ select: [id: string] }>();

const open = ref(false);
// Where the list actually opens. It starts where the placement says and flips if that would leave the window.
const alignEnd = ref(false);
const flipped = ref(false);
const root = ref<HTMLElement | null>(null);
const trigger = ref<HTMLButtonElement | null>(null);
const menu = ref<HTMLElement | null>(null);
const menuId = `${useId()}-menu`;
const itemId = (id: string) => `${menuId}-${id}`;

function itemButtons(): HTMLButtonElement[] {
  return Array.from(menu.value?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? []);
}
function focusItem(index: number) {
  const buttons = itemButtons();
  if (buttons.length) buttons[(index + buttons.length) % buttons.length].focus();
}
function keepInWindow() {
  const list = menu.value;
  if (!list) return;
  const margin = 8;
  let box = list.getBoundingClientRect();
  if (box.right > window.innerWidth - margin) {
    alignEnd.value = true;
    box = list.getBoundingClientRect();
  }
  // In a right-to-left layout, or on a narrow window, the end-aligned list can itself run off the start edge.
  if (box.left < margin) alignEnd.value = false;
  const vertical = list.getBoundingClientRect();
  if (vertical.bottom > window.innerHeight - margin || vertical.top < margin) flipped.value = true;
}
function outside(event: Event) {
  if (root.value && !root.value.contains(event.target as Node)) close(false);
}
async function show(at: "first" | "last") {
  if (props.disabled) return;
  open.value = true;
  document.addEventListener("pointerdown", outside, true);
  alignEnd.value = false;
  flipped.value = false;
  await nextTick();
  keepInWindow();
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
function choose(item: CorpusActionMenuItem) {
  if (item.reason) return; // Unavailable: leave the menu open so the reason stays readable.
  close(true);
  emit("select", item.id);
}
onBeforeUnmount(() => document.removeEventListener("pointerdown", outside, true));
</script>

<template>
  <div
    ref="root"
    class="action-menu"
    :data-placement="flipped ? (placement === 'top' ? 'bottom' : 'top') : placement"
    :data-align="alignEnd ? 'end' : 'start'"
  >
    <button
      ref="trigger"
      type="button"
      class="btn small action-menu-trigger"
      aria-haspopup="menu"
      :aria-expanded="open"
      :aria-controls="open ? menuId : undefined"
      :disabled="disabled"
      @click="toggle"
      @keydown="onTriggerKey"
    >
      <span class="action-menu-label">{{ label }}</span
      ><span class="action-menu-dots" aria-hidden="true"></span
      ><span class="action-menu-caret" aria-hidden="true"></span>
    </button>
    <ul
      v-if="open"
      :id="menuId"
      ref="menu"
      class="action-menu-list"
      role="menu"
      :aria-label="menuLabel || label"
      @keydown="onMenuKey"
    >
      <li v-for="item in items" :key="item.id" role="none">
        <button
          type="button"
          role="menuitem"
          class="action-menu-item"
          :aria-disabled="item.reason ? 'true' : undefined"
          :aria-describedby="item.reason ? itemId(item.id) : undefined"
          tabindex="-1"
          @click="choose(item)"
        >
          <span>{{ item.label }}</span>
          <small v-if="item.reason" :id="itemId(item.id)">{{ item.reason }}</small>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.action-menu {
  position: relative;
  display: inline-flex;
}
.action-menu-caret {
  display: inline-block;
  margin-inline-start: 8px;
  inline-size: 0.5rem;
  block-size: 0.5rem;
  border-inline-end: 2px solid currentColor;
  border-block-end: 2px solid currentColor;
  transform: translateY(-2px) rotate(45deg);
}
.action-menu[data-placement="top"] .action-menu-caret {
  transform: translateY(2px) rotate(-135deg);
}
.action-menu-dots {
  display: none;
  inline-size: 1.125rem;
  block-size: 0.25rem;
  background: radial-gradient(circle, currentColor 1.5px, transparent 2px) 0 50% / 0.375rem 100%
    repeat-x;
}
.action-menu-list {
  position: absolute;
  z-index: 30;
  inset-inline-start: 0;
  min-inline-size: 16rem;
  max-inline-size: min(22rem, calc(100vw - 16px));
  margin: 0;
  padding: 6px;
  list-style: none;
  border: 1px solid var(--line-strong);
  border-radius: 12px;
  background: var(--surface-overlay, var(--card));
  box-shadow: var(--elev-3, 0 12px 32px rgba(0, 0, 0, 0.2));
}
.action-menu[data-align="end"] .action-menu-list {
  inset-inline-start: auto;
  inset-inline-end: 0;
}
.action-menu[data-placement="top"] .action-menu-list {
  inset-block-end: calc(100% + 6px);
}
.action-menu[data-placement="bottom"] .action-menu-list {
  inset-block-start: calc(100% + 6px);
}
.action-menu-item {
  display: grid;
  gap: 2px;
  inline-size: 100%;
  min-block-size: 2.5rem;
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 650;
  text-align: start;
  cursor: pointer;
}
.action-menu-item:hover,
.action-menu-item:focus-visible {
  background: var(--soft);
}
.action-menu-item:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: -3px;
}
.action-menu-item[aria-disabled="true"] {
  color: var(--muted);
  cursor: not-allowed;
}
.action-menu-item small {
  font-size: 0.8125rem;
  font-weight: 500;
  line-height: 1.4;
  color: var(--muted);
}
@media (forced-colors: active) {
  .action-menu-list {
    border-color: CanvasText;
  }
  .action-menu-item:focus-visible {
    outline-color: Highlight;
  }
}
</style>
