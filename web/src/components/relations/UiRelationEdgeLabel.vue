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
    x: number;
    y: number;
    label: string;
    width?: number;
    height?: number;
  }>(),
  { width: 114, height: 20 },
);
</script>

<template>
  <g class="ui-relation-edge-label">
    <rect :x="x - width / 2" :y="y - height / 2" :width="width" :height="height" :rx="height / 2" />
    <text :x="x" :y="y + 4" text-anchor="middle">{{ label }}</text>
  </g>
</template>

<style scoped>
.ui-relation-edge-label rect {
  fill: var(--relation-edge-label-bg, var(--surface-overlay));
  stroke: var(--relation-edge-label-border, var(--border-subtle));
}
.ui-relation-edge-label text {
  fill: var(--relation-edge-label-fg, var(--text-secondary));
  font-size: 12px;
  font-weight: 700;
}
</style>
