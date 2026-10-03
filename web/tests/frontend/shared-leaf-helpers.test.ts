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
import { relativeTime } from "../../src/domain/sharedRelativeTime";
import {
  defaultProviderProfile,
  providerDisplayName,
} from "../../src/domain/sharedProviderProfiles";

describe("shared leaf helpers", () => {
  it("labels timestamps without the legacy runtime", () => {
    const justNow = relativeTime(new Date().toISOString());
    const hoursAgo = relativeTime(new Date(Date.now() - 2 * 3600 * 1000).toISOString());
    expect(justNow).not.toBe("");
    expect(hoursAgo).not.toBe("");
    expect(hoursAgo).not.toBe(justNow);
  });

  it("exposes provider helpers over the shared profile service", () => {
    expect(typeof defaultProviderProfile).toBe("function");
    expect(typeof providerDisplayName).toBe("function");
  });
});
