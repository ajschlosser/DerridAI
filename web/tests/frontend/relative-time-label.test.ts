/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { relativeTimeLabel } from "../../src/domain/relativeTimeLabel";

const now = Date.parse("2026-09-22T12:00:00Z");
const keys: string[] = [];
const deps = {
  tr: (_key: string, fallback: string) => fallback,
  trf: (key: string, fallback: string, values: Record<string, unknown>) => {
    keys.push(key);
    return fallback.replace("{count}", String(values.count));
  },
};
const ago = (ms: number) => new Date(now - ms).toISOString();

describe("relativeTimeLabel", () => {
  it("uses the singular only for exactly one unit", () => {
    expect(relativeTimeLabel(ago(60_000), now, deps)).toBe("1 minute ago");
    expect(relativeTimeLabel(ago(2 * 60_000), now, deps)).toBe("2 minutes ago");
    expect(relativeTimeLabel(ago(3_600_000), now, deps)).toBe("1 hour ago");
    expect(relativeTimeLabel(ago(5 * 3_600_000), now, deps)).toBe("5 hours ago");
    expect(relativeTimeLabel(ago(86_400_000), now, deps)).toBe("1 day ago");
    expect(relativeTimeLabel(ago(2 * 86_400_000), now, deps)).toBe("2 days ago");
  });

  it("asks the dictionary for the plural category so every locale can inflect", () => {
    keys.length = 0;
    relativeTimeLabel(ago(86_400_000), now, deps);
    relativeTimeLabel(ago(2 * 86_400_000), now, deps);
    expect(keys).toEqual(["time.days_ago_one", "time.days_ago_other"]);
  });

  it("keeps just now and unknown dates", () => {
    expect(relativeTimeLabel(ago(5_000), now, deps)).toBe("just now");
    expect(relativeTimeLabel("not a date", now, deps)).toBe("Recently");
  });
});
