<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import UiLoadingState from "../ui/UiLoadingState.vue";
import UiButton from "../ui/UiButton.vue";
defineProps<{ destination: string; failed?: boolean }>();
defineEmits<{ retry: []; reload: [] }>();
const i18n = useI18nStore();
</script>
<template>
  <div class="route-navigation-feedback">
    <template v-if="failed">
      <p role="alert">{{ i18n.tf("loading.navigation_failed", { destination }) }}</p>
      <div class="route-navigation-actions">
        <UiButton :label="i18n.t('ui.retry')" size="small" @click="$emit('retry')" />
        <UiButton :label="i18n.t('loading.reload_page')" size="small" @click="$emit('reload')" />
      </div>
    </template>
    <UiLoadingState
      v-else
      variant="inline"
      :label="i18n.tf('loading.navigation', { destination })"
    />
  </div>
</template>
<style scoped>
.route-navigation-feedback {
  position: fixed;
  inset-block-end: var(--space-5, 24px);
  inset-inline-end: var(--space-5, 24px);
  z-index: var(--z-popover, 100);
  max-inline-size: min(28rem, calc(100vw - 48px));
  padding: var(--space-3, 12px) var(--space-4, 16px);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-card, 12px);
  background: var(--surface-raised);
  color: var(--text-primary);
  box-shadow: var(--shadow-card);
  font-size: var(--fs-base, 0.875rem);
  overflow-wrap: anywhere;
}
.route-navigation-feedback p {
  margin: 0 0 var(--space-3, 12px);
}
.route-navigation-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
}
</style>
