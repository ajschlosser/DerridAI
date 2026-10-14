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
    label: string;
    tone?: "neutral" | "info" | "success" | "warning" | "danger";
    help?: string;
    showDot?: boolean;
  }>(),
  { tone: "neutral", help: "", showDot: true },
);
</script>
<template>
  <UiTooltip v-if="help" :text="help" placement="bottom" trigger-mode="content">
    <span v-bind="attrs" class="ui-status-badge" :data-tone="tone">
      <span v-if="showDot" class="ui-status-dot" aria-hidden="true"></span>{{ label }}
    </span>
  </UiTooltip>
  <span v-else v-bind="attrs" class="ui-status-badge" :data-tone="tone">
    <span v-if="showDot" class="ui-status-dot" aria-hidden="true"></span>{{ label }}
  </span>
</template>
<style scoped>
.ui-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 4px 9px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-inset);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: 700;
  line-height: 1.3;
  white-space: nowrap;
}
.ui-status-dot {
  inline-size: 8px;
  block-size: 8px;
  border-radius: 50%;
  background: var(--text-tertiary);
}
.ui-status-badge[data-tone="info"] {
  background: var(--tone-info-bg);
  border-color: var(--tone-info-edge);
  color: var(--tone-info-fg);
}
.ui-status-badge[data-tone="info"] .ui-status-dot {
  background: var(--tone-info-border);
}
.ui-status-badge[data-tone="success"] {
  background: var(--tone-ok-bg);
  border-color: var(--tone-ok-edge);
  color: var(--tone-ok-fg);
}
.ui-status-badge[data-tone="success"] .ui-status-dot {
  background: var(--tone-ok-border);
}
.ui-status-badge[data-tone="warning"] {
  background: var(--tone-warn-bg);
  border-color: var(--tone-warn-edge);
  color: var(--tone-warn-fg);
}
.ui-status-badge[data-tone="warning"] .ui-status-dot {
  background: var(--tone-warn-border);
}
.ui-status-badge[data-tone="danger"] {
  background: var(--tone-danger-bg);
  border-color: var(--tone-danger-edge);
  color: var(--tone-danger-fg);
}
.ui-status-badge[data-tone="danger"] .ui-status-dot {
  background: var(--tone-danger-border);
}
</style>
