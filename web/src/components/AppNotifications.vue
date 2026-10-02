<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useNotifications } from "../composables/notifications";
import { useI18nStore } from "../stores/i18n";

const { notifications, dismiss, pause, resume } = useNotifications();
const i18n = useI18nStore();
// A shape as well as a colour, so the tone is not carried by colour alone (WCAG 1.4.1).
const toneIcons = { success: "✓", info: "ℹ", warning: "⚠", danger: "✕" } as const;
</script>

<template>
  <section
    class="notifications"
    :aria-label="i18n.t('ui.notifications')"
    aria-live="polite"
    aria-atomic="false"
    aria-relevant="additions"
  >
    <div
      v-for="item in notifications"
      :key="item.id"
      class="notification"
      :data-tone="item.tone"
      tabindex="0"
      @pointerenter="pause(item.id)"
      @pointerleave="resume(item.id)"
      @focusin="pause(item.id)"
      @focusout="resume(item.id)"
      @keydown.esc="dismiss(item.id)"
    >
      <span class="notification-icon" aria-hidden="true">{{ toneIcons[item.tone] }}</span>
      <span class="sr-only">{{ i18n.t(`ui.notification_${item.tone}`) }}:</span>
      <span class="notification-message">{{ item.message }}</span>
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
  user-select: text;
}
.notification:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
/* Long values (a citation, a link) wrap rather than widen the notification. */
.notification-message {
  min-width: 0;
  overflow-wrap: anywhere;
}
.notification-icon {
  flex: 0 0 auto;
  font-weight: 700;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.notification[data-tone="success"] {
  border-left-color: var(--tone-ok-fg);
}
.notification[data-tone="success"] .notification-icon {
  color: var(--tone-ok-fg);
}
.notification[data-tone="warning"] .notification-icon {
  color: var(--tone-warn-fg);
}
.notification[data-tone="danger"] .notification-icon {
  color: var(--tone-danger-fg);
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
