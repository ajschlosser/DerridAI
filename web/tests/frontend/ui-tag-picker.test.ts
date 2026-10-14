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
import UiTagPicker from "../../src/components/ui/UiTagPicker.vue";

describe("UiTagPicker", () => {
  it("filters options without replacing selected values and emits selections", async () => {
    const wrapper = mount(UiTagPicker, {
      props: {
        modelValue: ["NOUN"],
        options: ["NOUN", "PROPN", "PRON", "VERB"],
        label: "POS tags",
        removeLabel: "Remove {value}",
      },
      attachTo: document.body,
    });

    const input = wrapper.get("input");
    await input.setValue("prop");

    expect(wrapper.text()).toContain("NOUN");
    expect(wrapper.text()).toContain("PROPN");
    expect(wrapper.text()).not.toContain("VERB");

    await wrapper.get('[role="option"]').trigger("mousedown");
    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual(["NOUN", "PROPN"]);

    wrapper.unmount();
  });

  it("announces the keyboard-active option through aria-activedescendant", async () => {
    const wrapper = mount(UiTagPicker, {
      props: {
        modelValue: [],
        options: ["NOUN", "PROPN"],
        label: "POS tags",
        removeLabel: "Remove {value}",
      },
    });

    const input = wrapper.get("input");
    await input.trigger("focus");
    await input.trigger("keydown", { key: "ArrowDown" });

    const activeId = input.attributes("aria-activedescendant");
    expect(activeId).toBeTruthy();
    expect(wrapper.get(`#${activeId}`).text()).toBe("NOUN");
  });

  it("removes a selected tag independently of the search query", async () => {
    const wrapper = mount(UiTagPicker, {
      props: {
        modelValue: ["PERSON", "ORG"],
        options: ["PERSON", "ORG", "WORK_OF_ART"],
        label: "NER tags",
        removeLabel: "Remove {value}",
      },
    });

    const remove = wrapper.get('button[aria-label="Remove PERSON"]');
    await remove.trigger("click");

    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual(["ORG"]);
  });

  it("shows descriptive option labels while persisting only the tag value", async () => {
    const wrapper = mount(UiTagPicker, {
      props: {
        modelValue: [],
        options: [
          { value: "PROPN", label: "Proper noun" },
          { value: "NOUN", label: "Common noun" },
        ],
        label: "POS tags",
        removeLabel: "Remove {value}",
      },
    });
    const input = wrapper.get('input[role="combobox"]');
    await input.setValue("proper");
    expect(wrapper.text()).toContain("PROPN");
    expect(wrapper.text()).toContain("Proper noun");
    await wrapper.get('[role="option"]').trigger("mousedown");
    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual(["PROPN"]);
  });
});
