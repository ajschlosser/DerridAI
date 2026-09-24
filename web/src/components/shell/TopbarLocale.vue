<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import type { LanguageInfo } from "../../api/system";
import type { UiMenuItem } from "../ui/UiMenu.vue";
import UiMenu from "../ui/UiMenu.vue";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{ languages: LanguageInfo[]; locale: string; loading?: boolean }>();
const emit = defineEmits<{ select: [code: string] }>();
const i18n = useI18nStore();
const currentName = computed(
  () => props.languages.find((language) => language.code === props.locale)?.name || props.locale,
);
const items = computed<UiMenuItem[]>(() =>
  props.languages.map((language) => ({
    id: language.code,
    label: language.name,
    checked: language.code === props.locale,
  })),
);
const triggerLabel = computed(() =>
  i18n.tf("ui.language_current", { language: currentName.value }),
);
</script>
<template>
  <UiMenu
    :label="currentName"
    :aria-label="triggerLabel"
    :menu-label="i18n.t('ui.language_menu')"
    :items="items"
    icon="language"
    placement="bottom"
    align="end"
    :disabled="loading"
    @select="emit('select', $event)"
  />
</template>
