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
