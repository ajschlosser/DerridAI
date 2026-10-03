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

import { describe, expect, it, vi } from "vitest";
import { notificationDuration, toast, useNotifications } from "../../src/composables/notifications";

describe("notification duration", () => {
  it("keeps short messages for the default time and gives long ones time to be read", () => {
    expect(notificationDuration("Role updated.")).toBe(4_200);
    expect(notificationDuration("x".repeat(150))).toBe(10_500);
    expect(notificationDuration("x".repeat(1_000))).toBe(20_000);
  });
});

describe("notification tone, pausing and bounds", () => {
  it("shows a message with the tone the caller states, and info by default", () => {
    const { notifications } = useNotifications();
    toast("Saved");
    toast("Careful", { tone: "warning" });
    expect(notifications.value.slice(-2).map((item) => item.tone)).toEqual(["info", "warning"]);
  });

  it("holds a notification while it is paused and dismisses it after resume", () => {
    vi.useFakeTimers();
    const { notifications, notify, pause, resume } = useNotifications();
    const id = notify("Saved", "info", { duration: 1000 });
    pause(id);
    vi.advanceTimersByTime(5000);
    expect(notifications.value.some((item) => item.id === id)).toBe(true);
    resume(id);
    vi.advanceTimersByTime(1000);
    expect(notifications.value.some((item) => item.id === id)).toBe(false);
    vi.useRealTimers();
  });

  it("keeps an error until it is dismissed", () => {
    vi.useFakeTimers();
    const { notifications, notify, dismiss } = useNotifications();
    const id = notify("Could not save", "danger");
    vi.advanceTimersByTime(60_000);
    expect(notifications.value.some((item) => item.id === id)).toBe(true);
    dismiss(id);
    expect(notifications.value.some((item) => item.id === id)).toBe(false);
    vi.useRealTimers();
  });

  it("keeps a bounded stack, dropping the oldest", () => {
    vi.useFakeTimers();
    const { notifications, notify } = useNotifications();
    const ids = Array.from({ length: 8 }, (_, index) => notify(`message ${index}`));
    expect(notifications.value).toHaveLength(5);
    expect(notifications.value[0].id).toBe(ids[3]);
    vi.runAllTimers();
    vi.useRealTimers();
  });
});
