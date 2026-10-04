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
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import ResearchWorkFilter from "../../src/components/research/ResearchWorkFilter.vue";

describe("ResearchWorkFilter", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("uses a labelled fieldset and exposes the all-works default", () => {
    const wrapper = mount(ResearchWorkFilter, {
      props: {
        modelValue: [],
        works: ["Glas", "Of Grammatology"],
        legendId: "scope",
      },
    });

    expect(wrapper.get("legend").attributes("id")).toBe("scope");
    expect(wrapper.get("fieldset").attributes("aria-describedby")).toBe("scope-help scope-status");
    expect(wrapper.get("[role=status]").attributes("aria-live")).toBe("polite");
    expect(wrapper.get("[role=status]").text()).toContain("All works included");
    expect(wrapper.findAll('input[type="checkbox"]')).toHaveLength(2);
  });

  it("emits exact selected works and can return to all works", async () => {
    const wrapper = mount(ResearchWorkFilter, {
      props: {
        modelValue: ["Glas"],
        works: ["Glas", "Of Grammatology"],
      },
    });

    const other = wrapper
      .findAll(".research-work-filter-options label")
      .find((label) => label.text().includes("Of Grammatology"));
    await other!.get("input").setValue(true);
    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual([
      "Glas",
      "Of Grammatology",
    ]);

    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("Include all works"))!
      .trigger("click");
    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual([]);
  });
});
