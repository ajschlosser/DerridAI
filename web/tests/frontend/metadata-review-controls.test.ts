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
import CorpusMetadataFieldEditor from "../../src/components/CorpusMetadataFieldEditor.vue";
import UiCombobox from "../../src/components/ui/UiCombobox.vue";
import CorpusMetadataResolutionPanel from "../../src/components/CorpusMetadataResolutionPanel.vue";

async function openList(modelValue: string, options: string[]) {
  const wrapper = mount(UiCombobox, {
    attachTo: document.body,
    props: { modelValue, label: "Topics", options, multiple: true },
  });
  await wrapper.get("[role=combobox]").trigger("focus");
  await wrapper.vm.$nextTick();
  return wrapper;
}
const menuItems = () => Array.from(document.body.querySelectorAll<HTMLElement>('[role="option"]'));

describe("list autocomplete toggles values", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("adds an absent value and removes a present one, showing the state in the menu", async () => {
    const wrapper = await openList("Kant", ["Kant", "Hegel", "Levinas"]);
    // Present values stay in the menu, marked selected (state is exposed to assistive tech too).
    const kant = menuItems().find((item) => item.textContent?.includes("Kant"))!;
    expect(kant.getAttribute("aria-selected")).toBe("true");
    expect(kant.getAttribute("data-selected")).toBe("true");
    const hegel = menuItems().find((item) => item.textContent?.includes("Hegel"))!;
    expect(hegel.getAttribute("aria-selected")).toBe("false");

    hegel.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }));
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["Kant, Hegel"]);
    await wrapper.setProps({ modelValue: "Kant, Hegel" });
    menuItems()
      .find((item) => item.textContent?.includes("Kant"))!
      .dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }));
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["Hegel"]);
    // The menu stays open so several changes can be made in one go.
    expect(menuItems().length).toBeGreaterThan(0);
    wrapper.unmount();
  });

  it("replaces half-typed text with the chosen value", async () => {
    const wrapper = await openList("Kant, Heg", ["Kant", "Hegel"]);
    menuItems()
      .find((item) => item.textContent?.includes("Hegel"))!
      .dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }));
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["Kant, Hegel"]);
    wrapper.unmount();
  });
});

describe("field editor decision controls", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("uses a text box, so long strings wrap, and never saves a star", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: { field: "concept", value: "", control: "text", open: true },
    });

    const box = wrapper.get("textarea");
    await box.setValue("★ Responsibility");
    await wrapper.get("[data-primary-action]").trigger("click");
    expect(wrapper.emitted("save")?.at(-1)).toEqual(["Responsibility"]);
  });

  it("marks an auto-filled value with a star that is text-alternative labelled", () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "stance",
        value: "affirm",
        control: "enum",
        options: ["affirm", "reject"],
        status: { status: "model_inferred", method: "llm", autofilled: true },
      },
    });
    expect(wrapper.get(".auto-star").text()).toBe("★");
    expect(wrapper.get(".field-current").text()).toContain("Auto-filled");
  });

  it("cites the reviewer's own knowledge from the one confirm button", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: { field: "concept", value: "trace", control: "text", open: true },
    });
    // Evidence tools live in the Cite evidence menu.
    await wrapper.get(".field-tools .action-menu-trigger").trigger("click");
    const toggle = Array.from(
      document.body.querySelectorAll<HTMLElement>('[role="menuitem"]'),
    ).find((item) => item.textContent?.includes("I know this"))!;
    toggle.click();
    await wrapper.vm.$nextTick();
    const primary = wrapper.get("[data-primary-action]");
    expect(primary.text()).toContain("own knowledge");
    await wrapper.get(".cite-self input").setValue("the introduction");
    await primary.trigger("click");
    expect(wrapper.emitted("saveWithHumanSource")?.at(-1)).toEqual(["trace", "the introduction"]);
    expect(wrapper.emitted("save")).toBeUndefined();
  });

  it("offers the traceability matrix on a decided field, saying whether memory shaped the answer", () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "concept",
        value: "trace",
        control: "text",
        memoryExamples: 3,
        status: {
          status: "model_inferred",
          method: "llm",
          llm_value: "trace",
          llm_confidence: 0.8,
        },
      },
    });
    expect(wrapper.find("input, textarea").exists()).toBe(false);
    const matrix = wrapper.get(".trace-matrix");
    expect(matrix.text()).toContain("metadata memory");
    expect(matrix.text()).toContain("80%");
  });
});

describe("metadata panel draft aggregation", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("keeps the panel dirty until every field draft is saved", async () => {
    const wrapper = mount(CorpusMetadataResolutionPanel, {
      props: {
        record: {
          record_id: "r1",
          text: "Derrida reports a position attributed to Levinas.",
          text_length: 49,
          source_block_ids: [],
          source_spans: [],
          speaker: "",
          position_holder: "",
          metadata_review_fields: ["speaker", "position_holder"],
        },
        regionTypes: [],
        discourseRoles: [],
      },
    });
    const editors = wrapper.findAllComponents(CorpusMetadataFieldEditor);
    const speaker = editors.find((editor) => editor.props("field") === "speaker")!;
    const holder = editors.find((editor) => editor.props("field") === "position_holder")!;
    await speaker.get("textarea").setValue("Derrida");
    await holder.get("textarea").setValue("Levinas");
    await speaker.get("[data-primary-action]").trigger("click");
    expect(wrapper.emitted("dirty")?.at(-1)).toEqual([true]);
    await holder.get("[data-primary-action]").trigger("click");
    expect(wrapper.emitted("dirty")?.at(-1)).toEqual([false]);

    await speaker.get("textarea").setValue("Another speaker");
    await holder.get("textarea").setValue("Another position holder");
    await speaker.get("[data-primary-action]").trigger("click");
    await holder.get("[data-primary-action]").trigger("click");
    expect(wrapper.emitted("resolve")?.slice(-2)).toEqual([
      ["speaker", "Another speaker"],
      ["position_holder", "Another position holder"],
    ]);
    expect(wrapper.emitted("dirty")?.at(-1)).toEqual([false]);
    wrapper.unmount();
  });
});
