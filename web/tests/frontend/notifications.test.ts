/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { notificationDuration } from "../../src/composables/notifications";

describe("notification duration", () => {
  it("keeps short messages for the default time and gives long ones time to be read", () => {
    expect(notificationDuration("Role updated.")).toBe(4_200);
    expect(notificationDuration("x".repeat(150))).toBe(10_500);
    expect(notificationDuration("x".repeat(1_000))).toBe(20_000);
  });
});
