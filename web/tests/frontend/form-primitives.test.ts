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
import UiCheckbox from "../../src/components/ui/UiCheckbox.vue";
import UiInput from "../../src/components/ui/UiInput.vue";
import UiSelect from "../../src/components/ui/UiSelect.vue";
import UiTextarea from "../../src/components/ui/UiTextarea.vue";

describe("ordinary form primitives", () => {
  it("keeps native input semantics and emits typed number values", async () => {
    const wrapper = mount(UiInput, {
      props: { modelValue: 0, type: "number", id: "threshold", min: 0, max: 1 },
    });
    const input = wrapper.get("input");
    expect(input.attributes("id")).toBe("threshold");
    expect(input.attributes("min")).toBe("0");
    await input.setValue("0.75");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([0.75]);
  });

  it("keeps native select semantics", async () => {
    const wrapper = mount(UiSelect, {
      props: { modelValue: "a" },
      slots: { default: '<option value="a">A</option><option value="b">B</option>' },
    });
    await wrapper.get("select").setValue("b");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["b"]);
  });

  it("associates invalid state with ordinary text controls", () => {
    const input = mount(UiInput, { props: { modelValue: "", invalid: true } });
    const textarea = mount(UiTextarea, { props: { modelValue: "", invalid: true } });
    expect(input.get("input").attributes("aria-invalid")).toBe("true");
    expect(textarea.get("textarea").attributes("aria-invalid")).toBe("true");
  });

  it("gives a checkbox a visible native label and optional description", async () => {
    const wrapper = mount(UiCheckbox, {
      props: { modelValue: false, label: "Require evidence", description: "A source span is required." },
    });
    const input = wrapper.get('input[type="checkbox"]');
    expect(wrapper.get("label").attributes("for")).toBe(input.attributes("id"));
    expect(input.attributes("aria-describedby")).toBeTruthy();
    await input.setValue(true);
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([true]);
  });
});
