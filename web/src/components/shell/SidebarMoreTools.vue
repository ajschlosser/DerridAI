<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import SidebarNavButton from "./SidebarNavButton.vue";
import type { SidebarNavEntry } from "./sidebarNav";

defineProps<{ items: SidebarNavEntry[]; open: boolean }>();
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
        :active="item.active"
        :disabled-reason="item.disabledReason"
        @navigate="$emit('navigate', $event)"
      />
    </div>
  </details>
</template>
