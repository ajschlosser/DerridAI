<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "../AppIcon.vue";

defineProps<{
  id: string;
  label: string;
  icon: string;
  active?: boolean;
  disabledReason?: string;
}>();
defineEmits<{ navigate: [string] }>();
</script>
<template>
  <span class="nav-tooltip-wrap" :data-tooltip="disabledReason || ''">
    <button
      type="button"
      :class="{ active }"
      :disabled="Boolean(disabledReason)"
      :aria-current="active ? 'page' : undefined"
      :aria-label="label"
      :aria-describedby="disabledReason ? `sidebar-nav-reason-${id}` : undefined"
      :title="disabledReason || label"
      @click="$emit('navigate', id)"
    >
      <AppIcon :name="icon" aria-hidden="true" /><span>{{ label }}</span>
    </button>
    <span v-if="disabledReason" :id="`sidebar-nav-reason-${id}`" class="sr-only">{{
      disabledReason
    }}</span>
  </span>
</template>
