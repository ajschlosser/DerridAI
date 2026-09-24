<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useNotifications } from "../composables/notifications";
import { useI18nStore } from "../stores/i18n";

const { notifications, dismiss } = useNotifications();
const i18n = useI18nStore();
</script>

<template>
  <section class="notifications" aria-live="polite" aria-atomic="true">
    <div v-for="item in notifications" :key="item.id" class="notification" :data-tone="item.tone">
      <span>{{ item.message }}</span>
      <button
        type="button"
        :aria-label="i18n.t('ui.dismiss_notification')"
        @click="dismiss(item.id)"
      >
        ×
      </button>
    </div>
  </section>
</template>

<style scoped>
.notifications {
  position: fixed;
  right: 1rem;
  bottom: 1rem;
  z-index: 40000;
  display: grid;
  gap: var(--space-2);
  max-width: min(28rem, calc(100vw - 2rem));
}
.notification {
  display: flex;
  align-items: start;
  gap: var(--space-3);
  padding: 0.75rem 0.9rem;
  border: 1px solid var(--border-strong);
  border-left-width: 3px;
  border-radius: var(--radius-control);
  background: var(--surface-overlay);
  color: var(--text-primary);
  box-shadow: var(--shadow-overlay);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
/* Long values (a citation, a link) wrap rather than widen the notification. */
.notification span {
  min-width: 0;
  overflow-wrap: anywhere;
}
.notification[data-tone="success"] {
  border-left-color: var(--tone-ok-fg);
}
.notification[data-tone="warning"] {
  border-left-color: var(--tone-warn-fg);
}
.notification[data-tone="danger"] {
  border-left-color: var(--tone-danger-fg);
}
.notification button {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  min-width: 24px;
  min-height: 24px;
  margin-left: auto;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
}
.notification button:hover {
  background: var(--surface-hover);
}
.notification button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
</style>
