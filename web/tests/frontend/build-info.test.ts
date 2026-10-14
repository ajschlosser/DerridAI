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
  APP_CODENAME,
  APP_GIT_COMMIT,
  APP_VERSION,
  COPYRIGHT_YEAR,
  appVersionLabel,
} from "../../src/buildInfo";
import pkg from "../../package.json";

describe("buildInfo", () => {
  it("uses the package release identity", () => {
    expect(APP_VERSION).toBe(pkg.version);
    expect(APP_CODENAME).toBe(pkg.codename);
  });

  it("pins the UI copyright year", () => {
    expect(COPYRIGHT_YEAR).toBe("2026");
  });

  it("combines version, codename, and commit", () => {
    expect(appVersionLabel("1.2.3", "abc1234", "Test Release")).toBe(
      "1.2.3 - Test Release (abc1234)",
    );
    expect(appVersionLabel("1.2.3", "", "Test Release")).toBe("1.2.3 - Test Release");
    expect(appVersionLabel("1.2.3", "", "")).toBe("1.2.3");
  });

  it("exposes a git commit string from the build", () => {
    expect(typeof APP_GIT_COMMIT).toBe("string");
  });
});
