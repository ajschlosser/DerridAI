<script setup lang="ts">
import AppIcon from "./AppIcon.vue";

const props = withDefaults(
  defineProps<{
    label: string;
    icon?: string;
    disabled?: boolean;
    disabledReason?: string;
    kind?: string;
    count?: number;
  }>(),
  {
    disabled: false,
    disabledReason: "",
    kind: "",
    count: 0,
  },
);

const emit = defineEmits<{ click: [] }>();
</script>

<template>
  <!-- The wrapper remains pointer-active when the button is disabled so the
       explanatory tooltip can still be shown. -->
  <span
    class="action-tooltip-wrap"
    :data-tooltip="props.disabled ? props.disabledReason : ''"
  >
    <button
      class="btn"
      :class="props.kind"
      :disabled="props.disabled"
      :aria-disabled="props.disabled"
      :title="props.disabled ? props.disabledReason : props.label"
      @click="emit('click')"
    >
      <AppIcon v-if="props.icon" :name="props.icon" />
      {{ props.label }}
      <span v-if="props.count" class="button-count">{{ props.count }}</span>
    </button>
  </span>
</template>
