<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import UiTooltip from "../ui/UiTooltip.vue";

defineProps<{
  id: string;
  label: string;
  icon: string;
  active?: boolean;
  disabledReason?: string;
}>();
defineEmits<{ navigate: [string] }>();
</script>

<template>
  <UiTooltip
    :text="disabledReason || label"
    trigger-mode="content"
    :content-focusable="Boolean(disabledReason)"
    placement="bottom"
  >
    <span class="nav-tooltip-wrap">
      <button
        type="button"
        :class="{ active }"
        :disabled="Boolean(disabledReason)"
        :aria-current="active ? 'page' : undefined"
        :aria-label="label"
        @click="$emit('navigate', id)"
      >
        <AppIcon :name="icon" aria-hidden="true" />
        <span>{{ label }}</span>
      </button>
    </span>
  </UiTooltip>
</template>

<style scoped>
.nav-tooltip-wrap {
  display: block;
  min-width: 0;
}

.nav-tooltip-wrap > button {
  position: relative;
  width: 100%;
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  box-shadow: none;
  color: var(--text-2);
  font-family: var(--font-ui);
  font-size: 0.8125rem;
  font-weight: 540;
  line-height: 1.25;
  text-align: left;
  cursor: pointer;
  transition:
    background-color var(--motion-fast, 120ms) var(--ease-standard, ease),
    color var(--motion-fast, 120ms) var(--ease-standard, ease),
    box-shadow var(--motion-fast, 120ms) var(--ease-standard, ease);
}

.nav-tooltip-wrap > button:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.nav-tooltip-wrap > button.active {
  background: var(--surface-selected);
  box-shadow: inset 2px 0 0 var(--ui-accent);
  color: var(--accent-fg);
  font-weight: var(--fw-semibold, 650);
}

.nav-tooltip-wrap > button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.nav-tooltip-wrap > button :deep(svg) {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: currentColor;
}

.nav-tooltip-wrap > button > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .nav-tooltip-wrap > button {
    transition: none;
  }
}

@media (forced-colors: active) {
  .nav-tooltip-wrap > button.active {
    outline: 2px solid CanvasText;
    outline-offset: -2px;
    box-shadow: none;
  }
}
</style>
