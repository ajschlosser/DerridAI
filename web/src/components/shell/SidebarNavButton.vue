<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  id: string;
  label: string;
  icon: string;
  collapsed?: boolean;
  active?: boolean;
  pending?: boolean;
  disabledReason?: string;
}>();
defineEmits<{ navigate: [string] }>();

const showTooltip = () => Boolean(props.collapsed || props.disabledReason);
</script>

<template>
  <UiTooltip
    v-if="showTooltip()"
    :text="disabledReason || label"
    trigger-mode="content"
    :content-focusable="Boolean(disabledReason)"
    placement="bottom"
  >
    <span class="nav-tooltip-wrap">
      <button
        type="button"
        :class="{ active, pending }"
        :disabled="Boolean(disabledReason)"
        :aria-current="active ? 'page' : undefined"
        :aria-busy="pending || undefined"
        :aria-label="label"
        @click="$emit('navigate', id)"
      >
        <AppIcon :name="icon" aria-hidden="true" />
        <span>{{ label }}</span>
      </button>
    </span>
  </UiTooltip>
  <span v-else class="nav-tooltip-wrap">
    <button
      type="button"
      :class="{ active, pending }"
      :disabled="Boolean(disabledReason)"
      :aria-current="active ? 'page' : undefined"
      :aria-busy="pending || undefined"
      :aria-label="label"
      @click="$emit('navigate', id)"
    >
      <AppIcon :name="icon" aria-hidden="true" />
      <span>{{ label }}</span>
    </button>
  </span>
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

.nav-tooltip-wrap > button.active,
.nav-tooltip-wrap > button.pending {
  background: var(--surface-selected);
  box-shadow:
    inset 3px 0 0 var(--ui-accent),
    0 0 0 1px color-mix(in srgb, var(--ui-accent) 12%, transparent);
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
  .nav-tooltip-wrap > button.active,
  .nav-tooltip-wrap > button.pending {
    outline: 2px solid CanvasText;
    outline-offset: -2px;
    box-shadow: none;
  }
}
</style>
