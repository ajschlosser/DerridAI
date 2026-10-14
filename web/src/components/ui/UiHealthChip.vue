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
import { useAttrs } from "vue";
import UiTooltip from "./UiTooltip.vue";

defineOptions({ inheritAttrs: false });
const attrs = useAttrs();

withDefaults(
  defineProps<{
    available?: boolean;
    label: string;
    detail?: string;
  }>(),
  { available: false, detail: "" },
);
</script>
<template>
  <UiTooltip v-if="detail" :text="detail" placement="bottom" trigger-mode="content">
    <span v-bind="attrs" class="ui-health-chip" :data-available="String(available)">
      <span class="ui-health-dot" aria-hidden="true"></span>
      <span>{{ label }}</span>
    </span>
  </UiTooltip>
  <span v-else v-bind="attrs" class="ui-health-chip" :data-available="String(available)">
    <span class="ui-health-dot" aria-hidden="true"></span>
    <span>{{ label }}</span>
  </span>
</template>
<style scoped>
.ui-health-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 4px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-inset);
  color: var(--text-primary);
  font-size: 0.8125rem;
  font-weight: 700;
}
.ui-health-dot {
  inline-size: 8px;
  block-size: 8px;
  border-radius: 50%;
  background: var(--tone-danger-fg);
}
.ui-health-chip[data-available="true"] {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
  color: var(--accent-fg);
}
.ui-health-chip[data-available="true"] .ui-health-dot {
  background: var(--accent);
}
</style>
