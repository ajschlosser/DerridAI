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
import { applyAppearance } from "../../src/domain/sharedAppearance";
import { selectedIndex, state } from "../../src/domain/sharedUrlState";

describe("shared appearance and selection helpers", () => {
  it("applies appearance preferences to the shared appConfig without the runtime", () => {
    const result = applyAppearance({ ui_color_scheme: "dark", ui_color_theme: "blue" });
    expect(state.appConfig.ui_color_scheme).toBe("dark");
    expect(state.appConfig.ui_color_theme).toBe("blue");
    expect(result.scheme).toBe("dark");
    expect(document.documentElement.dataset.uiTheme).toBe("blue");
  });

  it("falls back to system for an unknown scheme", () => {
    applyAppearance({ ui_color_scheme: "bogus" });
    expect(state.appConfig.ui_color_scheme).toBe("system");
  });

  it("clamps the selected record index to the file's records", () => {
    const file = { id: "f1", records: [{}, {}, {}] };
    state.selected = { f1: 9 };
    expect(selectedIndex(file)).toBe(2);
    state.selected = { f1: -3 };
    expect(selectedIndex(file)).toBe(0);
    expect(selectedIndex(null)).toBe(0);
  });
});
