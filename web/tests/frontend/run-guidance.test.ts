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
import CorpusRunGuidance from "../../src/components/CorpusRunGuidance.vue";

describe("Corpus run guidance", () => {
  beforeEach(() => setActivePinia(createPinia()));

  const persons = { name: "persons", label: "People", group: "indexing" };

  it("emits field-specific instructions and search cues as chips", async () => {
    const wrapper = mount(CorpusRunGuidance, { props: { fields: [persons], modelValue: {} } });
    await wrapper.find("textarea").setValue("Exclude bibliography-only mentions.");
    await wrapper.setProps({
      modelValue: wrapper.emitted("update:modelValue")?.at(-1)?.[0] as never,
    });
    const cues = wrapper.find("#run-guidance-terms-persons");
    await cues.setValue("Emmanuel Levinas");
    await cues.trigger("keydown", { key: "Enter" });
    await wrapper.setProps({
      modelValue: wrapper.emitted("update:modelValue")?.at(-1)?.[0] as never,
    });
    await cues.setValue("Levinas, levinas; Lévinas");
    await cues.trigger("keydown", { key: "Enter" });

    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual({
      persons: {
        instructions: "Exclude bibliography-only mentions.",
        look_for: ["Emmanuel Levinas", "Levinas", "Lévinas"],
        required: false,
      },
    });
  });

  it("removes a cue and toggles required review without inventing a fallback value", async () => {
    const wrapper = mount(CorpusRunGuidance, {
      props: {
        fields: [persons],
        modelValue: { persons: { instructions: "", look_for: ["A", "B"], required: false } },
      },
    });
    await wrapper.find(".rg-chip button").trigger("click");
    expect((wrapper.emitted("update:modelValue")?.at(-1)?.[0] as any).persons.look_for).toEqual([
      "B",
    ]);
    await wrapper.find('[role="switch"]').trigger("click");
    const last = (wrapper.emitted("update:modelValue")?.at(-1)?.[0] as any).persons;
    expect(last.required).toBe(true);
    expect(last).not.toHaveProperty("default_placeholder");
    expect(wrapper.text()).not.toContain("[not established in source]");
  });

  it("filters fields by search text and shows configured state", async () => {
    const wrapper = mount(CorpusRunGuidance, {
      props: {
        fields: [persons, { name: "work", label: "Work", group: "bibliography" }],
        modelValue: { work: { instructions: "Use title page", look_for: [] } },
      },
    });
    expect(wrapper.findAll(".rg-row")).toHaveLength(2);
    await wrapper.find('input[type="search"]').setValue("peo");
    expect(wrapper.findAll(".rg-row")).toHaveLength(1);
    await wrapper.find('input[type="search"]').setValue("");
    await wrapper.findAll(".rg-filters button")[1].trigger("click");
    expect(wrapper.findAll(".rg-row").map((row) => row.text())).toEqual([
      expect.stringContaining("Work"),
    ]);
  });

  it("imports guidance for matching schema fields", async () => {
    const wrapper = mount(CorpusRunGuidance, {
      props: {
        fields: [
          { name: "persons", label: "People", group: "indexing" },
          { name: "work", label: "Work", group: "bibliography" },
        ],
        modelValue: {},
      },
    });
    const input = wrapper.find('input[type="file"]');
    const file = new File(
      [
        JSON.stringify({
          format: "derridai-run-guidance",
          version: 1,
          guidance: {
            persons: {
              default_placeholder: "[not established in source]",
              instructions: "Check attribution.",
              look_for: ["First Name Last Name"],
              required: false,
            },
            obsolete: { instructions: "Ignore this field.", look_for: [] },
          },
        }),
      ],
      "guidance.json",
      { type: "application/json" },
    );
    Object.defineProperty(input.element, "files", { value: [file] });
    await input.trigger("change");

    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual({
      persons: {
        instructions: "Check attribution.",
        look_for: ["First Name Last Name"],
        required: false,
      },
    });
    expect(wrapper.find('[role="status"]').text()).toContain("imported");
  });
});
