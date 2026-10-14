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
import { useI18nStore } from "../stores/i18n";
const props = withDefaults(
  defineProps<{ modelValue?: "compact" | "roomy" | "cards"; label?: string }>(),
  { modelValue: "compact", label: "" },
);
const emit = defineEmits<{ "update:modelValue": [value: "compact" | "roomy" | "cards"] }>();
const i18n = useI18nStore();
const options: ["compact" | "roomy" | "cards", string][] = [
  ["compact", "search.layout_compact"],
  ["roomy", "search.layout_comfortable"],
  ["cards", "search.layout_cards"],
];
</script>
<template>
  <div
    class="search-layout-switcher"
    role="group"
    :aria-label="props.label || i18n.t('search.result_layout')"
  >
    <button
      v-for="[value, key] in options"
      :key="value"
      type="button"
      class="btn tiny"
      :class="{ active: props.modelValue === value }"
      :aria-pressed="props.modelValue === value"
      @click="emit('update:modelValue', value)"
    >
      {{ i18n.t(key) }}
    </button>
  </div>
</template>
