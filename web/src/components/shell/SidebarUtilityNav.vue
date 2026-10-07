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
import { useI18nStore } from "../../stores/i18n";
import SidebarNavButton from "./SidebarNavButton.vue";
import type { SidebarNavEntry } from "./sidebarNav";

defineProps<{ items: SidebarNavEntry[]; collapsed: boolean; pendingId?: string }>();
const emit = defineEmits<{ navigate: [string] }>();
const i18n = useI18nStore();
</script>

<template>
  <nav
    class="shell-utility-nav"
    :class="{ collapsed }"
    :aria-label="i18n.t('nav.utility_navigation')"
  >
    <SidebarNavButton
      v-for="item in items"
      :key="item.id"
      :id="item.id"
      :label="item.label"
      :icon="item.icon"
      :collapsed="collapsed"
      :active="item.active"
      :pending="item.id === pendingId"
      :disabled-reason="item.disabledReason"
      @navigate="emit('navigate', $event)"
    />
  </nav>
</template>

<style scoped>
.shell-utility-nav {
  display: grid;
  gap: 1px;
  flex: 0 0 auto;
  margin-top: 8px;
  padding: 12px 3px 0;
  border-top: 1px solid var(--line);
  font-family: var(--font-ui);
}

.shell-utility-nav :deep(.nav-tooltip-wrap > button) {
  min-height: 36px;
  border-radius: 9px;
  color: var(--muted);
}

.shell-utility-nav :deep(.nav-tooltip-wrap > button:hover),
.shell-utility-nav :deep(.nav-tooltip-wrap > button:focus-visible) {
  color: var(--text);
}

.shell-utility-nav :deep(.nav-tooltip-wrap > button.active) {
  color: var(--accent-fg);
}

.shell-utility-nav.collapsed {
  margin-top: 3px;
  padding-inline: 0;
}

.shell-utility-nav.collapsed :deep(.nav-tooltip-wrap > button) {
  justify-content: center;
  min-height: 40px;
  padding-inline: 8px;
  box-shadow: none;
}

.shell-utility-nav.collapsed :deep(.nav-tooltip-wrap > button.active) {
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ui-accent) 34%, transparent);
}

.shell-utility-nav.collapsed :deep(.nav-tooltip-wrap > button span) {
  display: none;
}

.shell-utility-nav.collapsed :deep(.nav-tooltip-wrap > button svg) {
  width: 18px;
  height: 18px;
}
</style>
