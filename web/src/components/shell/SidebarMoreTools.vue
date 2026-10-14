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
import AppIcon from "../AppIcon.vue";
import SidebarNavButton from "./SidebarNavButton.vue";
import type { SidebarNavEntry } from "./sidebarNav";

defineProps<{ items: SidebarNavEntry[]; open: boolean; collapsed?: boolean }>();
const emit = defineEmits<{ navigate: [string]; "update:open": [boolean] }>();
const i18n = useI18nStore();

function onToggle(event: Event) {
  emit("update:open", Boolean((event.currentTarget as HTMLDetailsElement)?.open));
}
</script>
<template>
  <details class="shell-more-tools" :open="open" @toggle="onToggle">
    <summary :aria-expanded="open">
      <span>{{ i18n.t("nav.more_tools") }}</span>
      <AppIcon name="chevron-down" aria-hidden="true" />
    </summary>
    <div class="shell-more-tools-list">
      <SidebarNavButton
        v-for="item in items"
        :key="item.id"
        :id="item.id"
        :label="item.label"
        :icon="item.icon"
        :collapsed="collapsed"
        :active="item.active"
        :disabled-reason="item.disabledReason"
        @navigate="$emit('navigate', $event)"
      />
    </div>
  </details>
</template>
