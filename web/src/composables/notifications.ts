import { readonly, ref } from "vue";

export type NotificationTone = "success" | "info" | "warning" | "danger";
export interface Notification { id: number; message: string; tone: NotificationTone; }

const notifications = ref<Notification[]>([]);
let nextId = 1;

export function notify(message: string, tone: NotificationTone = "info") {
  const id = nextId++;
  notifications.value = [...notifications.value, { id, message, tone }];
  window.setTimeout(() => dismiss(id), 4200);
}

export function dismiss(id: number) {
  notifications.value = notifications.value.filter(item => item.id !== id);
}

export function useNotifications() {
  return { notifications: readonly(notifications), notify, dismiss };
}
