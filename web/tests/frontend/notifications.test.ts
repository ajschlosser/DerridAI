/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import {
  inferNotificationTone,
  notificationDuration,
  useNotifications,
} from "../../src/composables/notifications";

describe("notification duration", () => {
  it("keeps short messages for the default time and gives long ones time to be read", () => {
    expect(notificationDuration("Role updated.")).toBe(4_200);
    expect(notificationDuration("x".repeat(150))).toBe(10_500);
    expect(notificationDuration("x".repeat(1_000))).toBe(20_000);
  });
});

describe("notification tone, pausing and bounds", () => {
  it("lets an explicit tone win over failure wording and reads the text otherwise", () => {
    expect(inferNotificationTone("Copied error log", "success")).toBe("success");
    expect(inferNotificationTone("Could not save", "info")).toBe("danger");
    expect(inferNotificationTone("Saved")).toBe("info");
    expect(inferNotificationTone("HTTP 500 from api")).toBe("danger");
    expect(inferNotificationTone("Careful", "warn")).toBe("warning");
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
