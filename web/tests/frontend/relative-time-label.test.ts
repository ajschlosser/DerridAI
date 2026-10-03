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

import { describe, expect, it } from "vitest";
import { relativeTimeLabel } from "../../src/domain/relativeTimeLabel";

const now = Date.parse("2026-09-22T12:00:00Z");
const keys: string[] = [];
const deps = {
  tr: (_key: string, fallback = "") => fallback,
  trf: (
    key: string,
    fallbackOrValues: string | Record<string, unknown> = "",
    values: Record<string, unknown> = {},
  ) => {
    keys.push(key);
    const fallback = typeof fallbackOrValues === "string" ? fallbackOrValues : "";
    const replacements = typeof fallbackOrValues === "string" ? values : fallbackOrValues;
    return fallback.replace("{count}", String(replacements.count));
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
