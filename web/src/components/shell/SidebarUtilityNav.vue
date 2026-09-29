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
  flex: 0 0 auto;
  margin-top: 4px;
  padding: 9px 3px 0;
  border-top: 1px solid var(--line);
  font-family: var(--font-ui);
}

.shell-utility-nav :deep(.nav-tooltip-wrap > button) {
  min-height: 36px;
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
