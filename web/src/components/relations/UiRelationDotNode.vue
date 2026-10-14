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
withDefaults(
  defineProps<{
    radius: number;
    label: string;
    showLabel?: boolean;
    labelOffset?: number;
  }>(),
  { showLabel: false, labelOffset: 5 },
);
</script>

<template>
  <g class="ui-relation-dot-node">
    <circle class="halo" :r="radius + 5" />
    <circle class="dot" :r="radius" />
    <text v-if="showLabel" class="label" :x="radius + labelOffset" y="4">
      {{ label }}
    </text>
  </g>
</template>

<style scoped>
.ui-relation-dot-node {
  cursor: grab;
  touch-action: none;
}
.halo {
  fill: none;
  stroke: var(--relation-node-halo, transparent);
  stroke-width: 3;
  stroke-opacity: var(--relation-node-halo-opacity, 1);
}
.dot {
  fill: var(--relation-node-dot, var(--hue, var(--accent)));
  fill-opacity: var(--relation-node-dot-opacity, 1);
  stroke: var(--relation-node-dot-border, var(--surface-raised));
  stroke-width: var(--relation-node-dot-border-width, 1.5);
}
.label {
  fill: var(--relation-node-label, var(--text-primary));
  font-size: 12px;
  font-weight: var(--fw-semibold);
  paint-order: stroke;
  stroke: var(--relation-node-label-halo, var(--surface-raised));
  stroke-width: 3px;
  stroke-linejoin: round;
  pointer-events: none;
}
</style>
