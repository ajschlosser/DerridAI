<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";

/** Tells a reader that newer server data exists without replacing what they are reading. */
defineProps<{ visible: boolean }>();
const emit = defineEmits<{ load: [] }>();
const i18n = useI18nStore();
</script>

<template>
  <div v-if="visible" class="newer-data-banner" role="status">
    <span>{{ i18n.t("realtime.newer_data") }}</span>
    <button type="button" class="newer-data-banner__action" @click="emit('load')">
      {{ i18n.t("realtime.load_newer") }}
    </button>
  </div>
</template>

<style scoped>
.newer-data-banner {
  display: flex;
  align-items: center;
  gap: var(--space-4, 0.75rem);
  padding: var(--space-3, 0.5rem) var(--space-4, 0.75rem);
  background: var(--surface-raised);
  border: 1px solid var(--border-strong, var(--border));
  border-radius: var(--radius-control);
  font-size: var(--fs-sm, 0.8125rem);
}
.newer-data-banner__action {
  margin-inline-start: auto;
}
</style>
