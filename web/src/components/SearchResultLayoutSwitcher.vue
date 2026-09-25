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
