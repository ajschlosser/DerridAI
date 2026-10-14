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

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import LanguageFlag from "../../src/components/LanguageFlag.vue";

describe("LanguageFlag", () => {
  it("shows the flag it is given and nothing keyed on the language code", () => {
    expect(mount(LanguageFlag, { props: { code: "fr-CA", symbol: "🇺🇸", label: "x" } }).text()).toBe(
      "🇺🇸",
    );
    expect(mount(LanguageFlag, { props: { code: "en-US", symbol: "🌐", label: "x" } }).text()).toBe(
      "🌐",
    );
  });

  it("falls back to the neutral globe when there is no flag, whatever the code", () => {
    for (const code of ["en-US", "fr-CA", "de-DE"]) {
      expect(mount(LanguageFlag, { props: { code, label: "x" } }).text()).toBe("🌐");
    }
  });
});
