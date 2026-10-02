/* Copyright 2026 Aaron John Schlosser, PhD. */
import { readonly, ref } from "vue";

export type NotificationTone = "success" | "info" | "warning" | "danger";
export interface Notification {
  id: number;
  message: string;
  tone: NotificationTone;
}
export interface NotifyOptions {
  /** Milliseconds before dismissal; defaults to a time scaled to the message length. */
  duration?: number | null;
}

/** The most notifications kept on screen; the oldest are dropped first. */
const MAX_NOTIFICATIONS = 5;

const notifications = ref<Notification[]>([]);
const durations = new Map<number, number>();
const timers = new Map<number, ReturnType<typeof setTimeout>>();
let nextId = 1;

/**
 * How long a notification stays: long enough to read. Messages that quote what was copied (a
 * citation, a link) are long, so the time grows with the length, up to 20 seconds.
 */
export function notificationDuration(message: string): number {
  return Math.min(20_000, Math.max(4_200, message.length * 70));
}

/**
 * The tone of a message from the legacy runtime, which passed free text and loose tone names. An
 * explicit success, warning or danger tone wins (copied record text may itself contain words like
 * "error"); anything else reads failure wording and HTTP statuses from the text, as the legacy
 * toast did.
 */
export function inferNotificationTone(message: string, tone = "auto"): NotificationTone {
  if (tone === "success" || tone === "danger" || tone === "warning") return tone;
  if (tone === "warn") return "warning";
  return /\bHTTP\s+\d{3}\b/i.test(message) || /\b(failed|could not|error)\b/i.test(message)
    ? "danger"
    : "info";
}

function schedule(id: number) {
  clearTimer(id);
  const delay = durations.get(id);
  if (delay === undefined) return;
  timers.set(
    id,
    setTimeout(() => dismiss(id), delay),
  );
}

function clearTimer(id: number) {
  const timer = timers.get(id);
  if (timer !== undefined) clearTimeout(timer);
  timers.delete(id);
}

export function notify(
  message: string,
  tone: NotificationTone = "info",
  options: NotifyOptions = {},
) {
  const id = nextId++;
  const kept = [...notifications.value, { id, message, tone }];
  for (const dropped of kept.slice(0, Math.max(0, kept.length - MAX_NOTIFICATIONS))) {
    dismiss(dropped.id);
  }
  notifications.value = [...notifications.value, { id, message, tone }];
  durations.set(id, options.duration ?? notificationDuration(message));
  schedule(id);
  return id;
}

/**
 * Show a message with the loose tone names the legacy runtime accepted (`"auto"` reads the wording).
 * Prefer `notify` with an explicit tone in new code.
 */
export function toast(
  message: string,
  { tone = "auto", duration = null }: { tone?: string; duration?: number | null } = {},
) {
  return notify(message, inferNotificationTone(message, tone), { duration });
}

export function dismiss(id: number) {
  clearTimer(id);
  durations.delete(id);
  notifications.value = notifications.value.filter((item) => item.id !== id);
}

/** Hold a notification while the pointer or keyboard focus is on it, so it can be read and copied. */
export function pause(id: number) {
  clearTimer(id);
}

/** Restart the dismissal timer once the pointer and focus have left the notification. */
export function resume(id: number) {
  if (durations.has(id)) schedule(id);
}

export function useNotifications() {
  return { notifications: readonly(notifications), notify, dismiss, pause, resume };
}
