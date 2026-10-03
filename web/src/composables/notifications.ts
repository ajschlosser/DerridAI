/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { readonly, ref } from "vue";

export type NotificationTone = "success" | "info" | "warning" | "danger";
export interface Notification {
  id: number;
  message: string;
  tone: NotificationTone;
}
export interface NotifyOptions {
  /** Milliseconds before dismissal; defaults to a time scaled to the message length (errors stay). */
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
  // An error stays until it is dismissed (button or Escape): disappearing on a timer would take it
  // from people who read slowly or use a screen reader (WCAG 2.2.1).
  const duration =
    options.duration ?? (tone === "danger" ? undefined : notificationDuration(message));
  if (duration !== undefined) durations.set(id, duration);
  schedule(id);
  return id;
}

/**
 * Show a message. The tone is always stated by the caller: it is announced to assistive technology
 * and shown beside the message, so it is never guessed from (language-specific) wording.
 */
export function toast(
  message: string,
  { tone = "info", duration = null }: { tone?: NotificationTone; duration?: number | null } = {},
) {
  return notify(message, tone, { duration });
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
