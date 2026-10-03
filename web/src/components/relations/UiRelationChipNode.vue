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
defineProps<{
  label: string;
}>();
</script>

<template>
  <span class="ui-relation-chip-node">
    <span class="ui-relation-chip-dot" aria-hidden="true"><slot name="dot" /></span>
    <span class="ui-relation-chip-label">{{ label }}</span>
  </span>
</template>

<style scoped>
.ui-relation-chip-node {
  display: inline-flex;
  max-width: 100%;
  min-width: 0;
  align-items: center;
  gap: 6px;
  padding: 2px 8px 2px 2px;
  border: 1px solid var(--relation-node-border, var(--border-subtle));
  border-radius: var(--radius-pill);
  background: var(--relation-node-bg, var(--surface-card));
  color: var(--relation-node-fg, var(--text-primary));
  box-shadow: var(--relation-node-shadow, none);
}
.ui-relation-chip-dot {
  width: 12px;
  height: 12px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--relation-node-dot, var(--accent-fg));
}
.ui-relation-chip-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (forced-colors: active) {
  .ui-relation-chip-node {
    border-color: ButtonText;
  }
  .ui-relation-chip-dot {
    border: 1px solid ButtonText;
    background: ButtonFace;
  }
}
</style>
