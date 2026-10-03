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
import { computed } from "vue";
import type { SettingsSectionId } from "../../domain/settings";

const props = defineProps<{
  modelValue: SettingsSectionId;
  items: Array<{ id: SettingsSectionId; label: string; path?: string }>;
  navLabel: string;
}>();
const emit = defineEmits<{
  select: [SettingsSectionId];
}>();

function activate(event: MouseEvent, id: SettingsSectionId) {
  if (
    event.defaultPrevented ||
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  ) {
    return;
  }
  event.preventDefault();
  emit("select", id);
}
const activeId = computed(() =>
  props.items.some((item) => item.id === props.modelValue)
    ? props.modelValue
    : props.items[0]?.id || "overview",
);
</script>
<template>
  <nav class="settings-nav" :aria-label="navLabel">
    <ul class="settings-nav-list">
      <li v-for="item in items" :key="item.id">
        <a
          :id="`settings-nav-${item.id}`"
          class="settings-nav-item"
          :class="{ active: item.id === activeId }"
          :href="item.path || `/settings/${item.id}`"
          :aria-current="item.id === activeId ? 'page' : undefined"
          @click="activate($event, item.id)"
        >
          {{ item.label }}
        </a>
      </li>
    </ul>
  </nav>
</template>
<style scoped>
.settings-nav {
  min-width: 0;
}
.settings-nav-list {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.settings-nav-item {
  min-height: 40px;
  width: 100%;
  display: flex;
  align-items: flex-start;
  text-align: left;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: var(--muted);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 700;
  line-height: 1.35;
}
.settings-nav-item.active {
  background: var(--accent-soft);
  border-color: var(--line-strong);
  color: var(--accent-fg);
  box-shadow: inset 3px 0 0 var(--accent);
}
.settings-nav-item:hover:not(.active) {
  background: var(--panel-2);
  color: var(--text);
}
.settings-nav-item:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
@media (forced-colors: active) {
  .settings-nav-item.active {
    outline: 2px solid CanvasText;
  }
}
</style>
