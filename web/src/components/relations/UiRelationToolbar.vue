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
import UiButton from "../ui/UiButton.vue";

withDefaults(
  defineProps<{
    accessibleLabel: string;
    zoomOutLabel: string;
    zoomInLabel: string;
    fitLabel: string;
    resetLabel: string;
    zoomText?: string;
    disabled?: boolean;
  }>(),
  {
    zoomText: "",
    disabled: false,
  },
);

const emit = defineEmits<{
  zoomOut: [];
  zoomIn: [];
  fit: [];
  reset: [];
}>();
</script>

<template>
  <div class="ui-relation-toolbar" role="group" :aria-label="accessibleLabel">
    <slot name="before" />
    <UiButton
      :label="zoomOutLabel"
      size="small"
      variant="ghost"
      :disabled="disabled"
      @click="emit('zoomOut')"
    />
    <span v-if="zoomText" class="ui-relation-toolbar-zoom" aria-live="polite">{{ zoomText }}</span>
    <UiButton
      :label="zoomInLabel"
      size="small"
      variant="ghost"
      :disabled="disabled"
      @click="emit('zoomIn')"
    />
    <UiButton
      :label="fitLabel"
      size="small"
      variant="ghost"
      :disabled="disabled"
      @click="emit('fit')"
    />
    <UiButton
      :label="resetLabel"
      size="small"
      variant="ghost"
      :disabled="disabled"
      @click="emit('reset')"
    />
    <slot name="after" />
  </div>
</template>

<style scoped>
.ui-relation-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}
.ui-relation-toolbar-zoom {
  min-width: 4.5ch;
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
  text-align: center;
}
</style>
