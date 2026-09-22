/* Copyright 2026 Aaron John Schlosser, PhD. */
import { readonly, ref } from "vue";

export type NotificationTone = "success" | "info" | "warning" | "danger";
export interface Notification {
  id: number;
  message: string;
  tone: NotificationTone;
}

const notifications = ref<Notification[]>([]);
let nextId = 1;

/**
 * How long a notification stays: long enough to read. Messages that quote what was copied (a
 * citation, a link) are long, so the time grows with the length, up to 20 seconds.
 */
export function notificationDuration(message: string): number {
  return Math.min(20_000, Math.max(4_200, message.length * 70));
}

export function notify(message: string, tone: NotificationTone = "info") {
  const id = nextId++;
  notifications.value = [...notifications.value, { id, message, tone }];
  window.setTimeout(() => dismiss(id), notificationDuration(message));
}

export function dismiss(id: number) {
  notifications.value = notifications.value.filter((item) => item.id !== id);
}

export function useNotifications() {
  return { notifications: readonly(notifications), notify, dismiss };
}
