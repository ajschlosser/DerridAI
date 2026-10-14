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
import BrandMark from "../../src/components/BrandMark.vue";

describe("BrandMark", () => {
  it("is decorative and does not duplicate the localized product name", () => {
    const wrapper = mount(BrandMark);
    const mark = wrapper.get(".brand-mark");

    expect(mark.attributes("aria-hidden")).toBe("true");
    expect(wrapper.get("img").attributes("alt")).toBe("");
  });
});
