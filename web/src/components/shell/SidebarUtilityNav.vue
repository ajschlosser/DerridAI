<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import SidebarNavButton from "./SidebarNavButton.vue";
import type { SidebarNavEntry } from "./sidebarNav";

defineProps<{ items: SidebarNavEntry[]; collapsed: boolean }>();
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
      :active="item.active"
      :disabled-reason="item.disabledReason"
      @navigate="emit('navigate', $event)"
    />
  </nav>
</template>

<style scoped>
.shell-utility-nav {
  display: grid;
  gap: 1px;
  padding: 8px 2px 0;
  border-top: 1px solid var(--line);
}
.shell-utility-nav.collapsed {
  padding-inline: 0;
}
.shell-utility-nav.collapsed :deep(.nav-tooltip-wrap > button) {
  justify-content: center;
  min-height: 40px;
  padding-inline: 8px;
}
.shell-utility-nav.collapsed :deep(.nav-tooltip-wrap > button span) {
  display: none;
}
.shell-utility-nav.collapsed :deep(.nav-tooltip-wrap > button svg) {
  width: 18px;
  height: 18px;
}
</style>
