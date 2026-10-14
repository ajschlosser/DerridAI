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
import UiCombobox from "../../src/components/ui/UiCombobox.vue";

const mountCombo = (modelValue: string, multiple = false) =>
  mount(UiCombobox, {
    props: {
      modelValue,
      options: ["affirm", "describe", "neutral"],
      recommended: ["Describe"],
      recommendedLabel: "Suggested",
      label: "Stance",
      multiple,
    },
  });

describe("choice combobox suggested value", () => {
  it("marks the field itself with the star when its value is the suggestion", () => {
    const wrapper = mountCombo("describe");
    const badge = wrapper.find('[data-testid="combo-value-recommended"]');
    expect(badge.text()).toContain("★");
    expect(wrapper.find("input").attributes("aria-describedby")).toBe(badge.attributes("id"));
  });

  it("drops the star once the reviewer picks something else", () => {
    const wrapper = mountCombo("neutral");
    expect(wrapper.find('[data-testid="combo-value-recommended"]').exists()).toBe(false);
    expect(wrapper.find("input").attributes("aria-describedby")).toBeUndefined();
  });
});
