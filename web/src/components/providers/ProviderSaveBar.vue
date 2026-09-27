<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";

// Appears only while there are unsaved changes, so the page is silent otherwise.
defineProps<{ saving: boolean; canSave: boolean }>();
defineEmits<{ save: []; discard: [] }>();
const i18n = useI18nStore();
</script>

<template>
  <div class="providers-save" role="region" :aria-label="i18n.t('providers.unsaved_changes')">
    <span class="providers-save-note" role="status">{{ i18n.t("providers.unsaved_changes") }}</span>
    <button class="btn" type="button" :disabled="saving" @click="$emit('discard')">
      {{ i18n.t("providers.discard") }}
    </button>
    <button class="btn primary" type="button" :disabled="saving || !canSave" @click="$emit('save')">
      {{ saving ? i18n.t("ui.saving") : i18n.t("ui.save") }}
    </button>
  </div>
</template>

<style scoped>
.providers-save {
  position: sticky;
  bottom: 12px;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius-card);
  background: var(--raised);
  box-shadow: var(--shadow-md, var(--shadow-sm));
}
.providers-save-note {
  margin-inline-end: auto;
  font-size: 0.875rem;
  font-weight: 650;
}
.providers-save-enter-active,
.providers-save-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}
.providers-save-enter-from,
.providers-save-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
@media (prefers-reduced-motion: reduce) {
  .providers-save-enter-active,
  .providers-save-leave-active {
    transition: none;
  }
}
</style>
