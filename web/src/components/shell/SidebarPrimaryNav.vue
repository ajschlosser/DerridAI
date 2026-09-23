<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import SidebarNavButton from "./SidebarNavButton.vue";
import type { SidebarNavEntry } from "./sidebarNav";

defineProps<{ items: SidebarNavEntry[] }>();
defineEmits<{ navigate: [string] }>();
const i18n = useI18nStore();
</script>
<template>
  <nav class="side-nav shell-primary-nav" :aria-label="i18n.t('ui.primary_navigation')">
    <SidebarNavButton
      v-for="item in items"
      :key="item.id"
      :id="item.id"
      :label="item.label"
      :icon="item.icon"
      :active="item.active"
      :disabled-reason="item.disabledReason"
      @navigate="$emit('navigate', $event)"
    />
  </nav>
</template>
