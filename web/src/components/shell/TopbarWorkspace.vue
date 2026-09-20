<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import type { UiMenuItem } from "../ui/UiMenu.vue";
import UiMenu from "../ui/UiMenu.vue";
import { useI18nStore } from "../../stores/i18n";

defineProps<{ items: UiMenuItem[] }>();
const emit = defineEmits<{ select: [id: string] }>();
const i18n = useI18nStore();
</script>
<template>
  <UiMenu
    :label="i18n.t('ui.workspace_menu', 'Workspace')"
    :items="items"
    icon="list"
    placement="bottom"
    align="end"
    @select="emit('select', $event)"
  />
</template>
