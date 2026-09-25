<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";

const props = withDefaults(
  defineProps<{
    field: string;
    fieldLabel: string;
    count: number;
    compact?: boolean;
  }>(),
  { compact: false },
);
const emit = defineEmits<{ inspect: [field: string] }>();
const i18n = useI18nStore();
</script>
<template>
  <button
    type="button"
    class="mixed-value-inspect"
    :class="{ compact: props.compact }"
    :data-inspect-mixed-field="props.field"
    :aria-label="
      i18n.tf('works.inspect_mixed_aria', { count: props.count, field: props.fieldLabel })
    "
    @click.stop="emit('inspect', props.field)"
  >
    <span>{{ i18n.t("works.mixed") }}</span>
    <b>{{ props.count }}</b>
    <small>{{ i18n.t("works.unique_values") }}</small>
  </button>
</template>
