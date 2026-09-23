<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";
import { useI18nStore } from "../stores/i18n";

/**
 * "Get Citation": a menu button offering the inline and full citation. The menu is a native
 * popover so it escapes scrolling table cells; it closes on a choice, on Escape, or on a click
 * elsewhere, and returns focus to the button.
 */
const props = withDefaults(defineProps<{ compact?: boolean; label?: string }>(), {
  compact: false,
  label: "",
});
const emit = defineEmits<{ inline: []; full: [] }>();

const i18n = useI18nStore();
const button = ref<HTMLButtonElement | null>(null);
const popover = ref<HTMLElement | null>(null);
const expanded = ref(false);
const id = `citation-${useId().replaceAll(":", "-")}`;
const menuLabel = computed(() => props.label || i18n.t("ui.get_citation"));
const buttonClass = computed(() => (props.compact ? "btn tiny" : "btn"));
const VIEWPORT_PADDING = 8;
const GAP = 5;

function items(): HTMLButtonElement[] {
  return [...(popover.value?.querySelectorAll<HTMLButtonElement>("[role=menuitem]") || [])];
}

/**
 * Place the open menu under the button, right-aligned, and flip it above when there is no room
 * below. Never set `display` here: an inline display would override the closed popover's
 * `display: none` and leave the menu on screen after it closes.
 */
function place() {
  const trigger = button.value;
  const panel = popover.value;
  if (!trigger || !panel?.matches(":popover-open")) return;
  const rect = trigger.getBoundingClientRect();
  const width = panel.offsetWidth;
  const height = panel.offsetHeight;
  const left = Math.max(
    VIEWPORT_PADDING,
    Math.min(rect.right - width, window.innerWidth - width - VIEWPORT_PADDING),
  );
  const below = rect.bottom + GAP;
  const top =
    below + height > window.innerHeight - VIEWPORT_PADDING
      ? Math.max(VIEWPORT_PADDING, rect.top - height - GAP)
      : below;
  panel.style.left = `${Math.round(left)}px`;
  panel.style.top = `${Math.round(top)}px`;
}

function hide() {
  (popover.value as (HTMLElement & { hidePopover?: () => void }) | null)?.hidePopover?.();
}

async function onToggle(event: Event) {
  expanded.value = (event.currentTarget as HTMLElement).matches(":popover-open");
  if (!expanded.value) return;
  await nextTick();
  place();
  items()[0]?.focus();
}

function onMenuKeydown(event: KeyboardEvent) {
  const list = items();
  const at = list.indexOf(document.activeElement as HTMLButtonElement);
  const move: Record<string, number> = {
    ArrowDown: (at + 1) % list.length,
    ArrowUp: (at - 1 + list.length) % list.length,
    Home: 0,
    End: list.length - 1,
  };
  if (event.key in move) {
    event.preventDefault();
    list[move[event.key]]?.focus();
  } else if (event.key === "Escape" || event.key === "Tab") {
    // The popover closes itself on Escape; either way focus goes back to the button.
    if (event.key === "Escape") event.preventDefault();
    hide();
    button.value?.focus();
  }
}

function choose(kind: "inline" | "full") {
  hide();
  if (kind === "inline") emit("inline");
  else emit("full");
  button.value?.focus();
}
</script>

<template>
  <span class="citation-menu-native">
    <button
      ref="button"
      type="button"
      :class="buttonClass"
      :popovertarget="id"
      aria-haspopup="menu"
      :aria-expanded="expanded"
      :aria-controls="id"
    >
      {{ menuLabel }}<span class="citation-menu-chevron" aria-hidden="true">▾</span>
    </button>
    <div
      :id="id"
      ref="popover"
      class="citation-popover-native"
      popover="auto"
      role="menu"
      :aria-label="menuLabel"
      @toggle="onToggle"
      @keydown="onMenuKeydown"
    >
      <button
        type="button"
        role="menuitem"
        tabindex="-1"
        :class="buttonClass"
        @click="choose('inline')"
      >
        {{ i18n.t("ui.inline") }}
      </button>
      <button
        type="button"
        role="menuitem"
        tabindex="-1"
        :class="buttonClass"
        @click="choose('full')"
      >
        {{ i18n.t("ui.full") }}
      </button>
    </div>
  </span>
</template>
