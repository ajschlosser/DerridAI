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
import {
  detectInstalledBrowserLocale,
  normalizeLocale,
  resolveTimeZone,
  supportedTimeZones,
} from "../../src/domain/localePreferences";

const installed = [{ code: "en-US" }, { code: "fr-CA" }, { code: "de-DE" }];

describe("locale preferences", () => {
  it("matches the browser's first preferred locale exactly or by base language", () => {
    expect(detectInstalledBrowserLocale(installed, ["de-DE"]).match).toBe("de-DE");
    expect(detectInstalledBrowserLocale(installed, ["fr-FR"]).match).toBe("fr-CA");
  });

  it("does not skip an unavailable first browser language", () => {
    expect(detectInstalledBrowserLocale(installed, ["hi-IN", "fr-FR"])).toEqual({
      requested: "hi-IN",
      match: null,
    });
    expect(normalizeLocale("fr_CA")).toBe("fr-CA");
  });

  it("uses a valid explicit timezone and otherwise the browser timezone", () => {
    expect(resolveTimeZone("UTC", "America/Los_Angeles")).toBe("UTC");
    expect(resolveTimeZone("not/a-zone", "America/Los_Angeles")).toBe("America/Los_Angeles");
    expect(supportedTimeZones("America/Los_Angeles")).toContain("America/Los_Angeles");
  });
});
