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
import { nextTick } from "vue";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusMetadataResolutionPanel from "../../src/components/CorpusMetadataResolutionPanel.vue";
import CorpusMetadataFieldEditor from "../../src/components/CorpusMetadataFieldEditor.vue";

const pending = { status: "unresolved", method: "llm", confidence: 0.8 };
function record(over: Record<string, unknown> = {}) {
  return {
    record_id: "r1",
    text: "A passage.",
    stance: "affirm",
    discourse_role: "assertion",
    speaker: "Jacques Derrida",
    metadata_review_fields: ["stance", "discourse_role", "speaker"],
    metadata_incomplete_fields: [],
    metadata_field_status: { stance: pending, discourse_role: pending, speaker: pending },
    ...over,
  } as never;
}
const mountPanel = (props: Record<string, unknown> = {}) =>
  mount(CorpusMetadataResolutionPanel, {
    props: {
      record: record(),
      regionTypes: ["main_text"],
      discourseRoles: ["assertion", "critique"],
      ...props,
    },
    attachTo: document.body,
  });
const cards = (wrapper: ReturnType<typeof mountPanel>) =>
  wrapper.findAll(".decision-list [data-field]").map((card) => card.attributes("data-field"));

describe("adjudicating a record's metadata", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("lists the fields the server requires first, marked, and every pending field open", () => {
    const wrapper = mountPanel({ blockingFields: ["speaker"] });
    expect(cards(wrapper)[0]).toBe("speaker");
    const first = wrapper.get('.decision-list [data-field="speaker"]');
    expect(first.text()).toContain("Required to accept");
    expect(wrapper.findAll('.decision-list [data-mode="edit"]')).toHaveLength(3);
    wrapper.unmount();
  });

  it("keeps a decided field in place, folded to one line, instead of moving it to another list", async () => {
    const wrapper = mountPanel();
    const before = cards(wrapper);
    await wrapper.setProps({
      record: record({
        metadata_review_fields: ["discourse_role", "speaker"],
        metadata_field_status: {
          stance: { status: "human_confirmed", method: "human" },
          discourse_role: pending,
          speaker: pending,
        },
      }),
    });
    expect(cards(wrapper)).toEqual(before);
    expect(wrapper.get('[data-field="stance"]').attributes("data-mode")).toBe("view");
    expect(wrapper.find(".settled-metadata [data-field='stance']").exists()).toBe(false);
    wrapper.unmount();
  });

  it("moves focus to the next field's Confirm after a decision, and reports completion after the last", async () => {
    const wrapper = mountPanel();
    const [first, second] = cards(wrapper);
    await wrapper.get(`[data-field="${first}"] [data-primary-action]`).trigger("click");
    await nextTick();
    await nextTick();
    expect(document.activeElement).toBe(
      wrapper.get(`[data-field="${second}"] [data-primary-action]`).element,
    );
    expect(wrapper.emitted("resolve")?.[0]?.[0]).toBe(first);

    // Only one field left: deciding it hands the record decision back to the workspace.
    await wrapper.setProps({
      record: record({
        metadata_review_fields: ["speaker"],
        metadata_field_status: {
          stance: { status: "human_confirmed" },
          discourse_role: { status: "human_confirmed" },
          speaker: pending,
        },
      }),
    });
    await wrapper.get('[data-field="speaker"] [data-primary-action]').trigger("click");
    await nextTick();
    await nextTick();
    expect(wrapper.emitted("complete")).toHaveLength(1);
    wrapper.unmount();
  });

  it("honors an explicit saving prop before moving focus", async () => {
    // The panel still supports a caller that deliberately holds a field in a
    // saving state, even though Record Review releases optimistic decisions immediately.
    const wrapper: ReturnType<typeof mountPanel> = mountPanel({
      onResolve: (field: string) => void wrapper.setProps({ savingField: field }),
    });
    const [first, second] = cards(wrapper);
    await wrapper.get(`[data-field="${first}"] [data-primary-action]`).trigger("click");
    await nextTick();
    await nextTick();
    expect(document.activeElement).not.toBe(
      wrapper.get(`[data-field="${second}"] [data-primary-action]`).element,
    );
    await wrapper.setProps({ savingField: "" });
    await nextTick();
    await nextTick();
    expect(document.activeElement).toBe(
      wrapper.get(`[data-field="${second}"] [data-primary-action]`).element,
    );
    wrapper.unmount();
  });

  it("never steals focus from another field the reviewer started editing while a save settles", async () => {
    const wrapper: ReturnType<typeof mountPanel> = mountPanel({
      onResolve: (field: string) => void wrapper.setProps({ savingField: field }),
    });
    const [first, second] = cards(wrapper);
    if (!first || !second) throw new Error("At least two pending fields are required.");

    await wrapper.get(`[data-field="${first}"] [data-primary-action]`).trigger("click");
    await nextTick();
    const editor = wrapper.get('[data-field="speaker"] textarea');
    (editor.element as HTMLTextAreaElement).focus();
    await editor.setValue("Reviewer is typing here");
    expect(document.activeElement).toBe(editor.element);

    await wrapper.setProps({ savingField: "" });
    await nextTick();
    await nextTick();

    expect(document.activeElement).toBe(editor.element);
    expect(document.activeElement).not.toBe(
      wrapper.get(`[data-field="${second}"] [data-primary-action]`).element,
    );
    wrapper.unmount();
  });

  it("includes model-suggested absences when accepting all LLM suggestions", async () => {
    const wrapper = mountPanel({
      record: record({
        stance: "no value",
        metadata_review_fields: ["stance", "speaker"],
        metadata_field_status: {
          stance: {
            status: "unresolved",
            method: "llm",
            derivation_method: "model",
          },
          speaker: pending,
        },
      }),
    });

    const saveAll = wrapper.get(".suggestion-toolbar button");
    await saveAll.trigger("click");

    expect(wrapper.emitted("resolveMany")?.[0]).toEqual([
      { stance: null, speaker: "Jacques Derrida" },
      ["stance"],
    ]);
    wrapper.unmount();
  });

  it("focuses No value when the next field has no proposal and advances after that decision", async () => {
    const wrapper = mountPanel();
    const [first, second, third] = cards(wrapper);
    if (!first || !second || !third) throw new Error("Three pending fields are required.");
    await wrapper.setProps({ record: record({ [second]: "" }) });
    await wrapper.get(`[data-field="${first}"] [data-primary-action]`).trigger("click");
    await nextTick();
    await nextTick();
    const noValue = wrapper.get(`[data-field="${second}"] [data-no-value-action]`);
    expect(document.activeElement).toBe(noValue.element);
    expect(noValue.attributes("data-primary-action")).toBeDefined();
    expect(wrapper.emitted("noValue")).toBeUndefined();
    await noValue.trigger("keydown", { key: "Enter" });
    await nextTick();
    await nextTick();
    expect(wrapper.emitted("noValue")).toEqual([[second]]);
    expect(document.activeElement).toBe(
      wrapper.get(`[data-field="${third}"] [data-primary-action]`).element,
    );
    wrapper.unmount();
  });
});

describe("a field's decision controls", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("confirms with Ctrl+Enter from inside the value control", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "stance",
        value: "affirm",
        control: "enum",
        options: ["affirm", "reject"],
        open: true,
        status: pending,
      },
    });
    await wrapper.get("select").trigger("keydown", { key: "Enter", ctrlKey: true });
    expect(wrapper.emitted("save")).toEqual([["affirm"]]);
    wrapper.unmount();
  });

  it.each([{ value: "" }, { value: null }, { value: [] }])(
    "defaults an empty proposal $value to No value",
    async ({ value }) => {
      const wrapper = mount(CorpusMetadataFieldEditor, {
        props: { field: "topics", value, control: "multi-combobox", open: true, status: pending },
      });
      expect(wrapper.get("[data-primary-action]").attributes("data-no-value-action")).toBeDefined();
      expect(wrapper.emitted("noValue")).toBeUndefined();
      await wrapper.get("textarea").trigger("keydown", { key: "Enter", ctrlKey: true });
      expect(wrapper.emitted("noValue")).toEqual([[]]);
      expect(wrapper.emitted("save")).toBeUndefined();
      wrapper.unmount();
    },
  );

  it.each([
    { value: false, control: "boolean" as const },
    { value: 0, control: "number" as const },
  ])("keeps a false/zero proposal $value on its value decision", ({ value, control }) => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: { field: "custom", value, control, open: true },
    });
    expect(wrapper.get("[data-primary-action]").attributes("data-no-value-action")).toBeUndefined();
    wrapper.unmount();
  });

  it("switches the primary decision to Save when the reviewer supplies a value", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: { field: "speaker", value: "", control: "text", open: true, status: pending },
    });
    expect(wrapper.get("[data-primary-action]").attributes("data-no-value-action")).toBeDefined();
    await wrapper.get("textarea").setValue("Reviewed speaker");
    expect(wrapper.get("[data-primary-action]").attributes("data-no-value-action")).toBeUndefined();
    await wrapper.get("textarea").trigger("keydown", { key: "Enter", metaKey: true });
    expect(wrapper.emitted("save")).toEqual([["Reviewed speaker"]]);
    expect(wrapper.emitted("noValue")).toBeUndefined();
    wrapper.unmount();
  });

  it.each([{ busy: true }, { saving: true }])(
    "does not confirm absence while a decision is unavailable: %j",
    async (availability) => {
      const wrapper = mount(CorpusMetadataFieldEditor, {
        props: { field: "speaker", value: "", control: "text", open: true, ...availability },
      });
      expect(wrapper.get("[data-primary-action]").attributes("disabled")).toBeDefined();
      await wrapper.get("textarea").trigger("keydown", { key: "Enter", ctrlKey: true });
      expect(wrapper.emitted("noValue")).toBeUndefined();
      wrapper.unmount();
    },
  );

  it("says Confirm for a proposed value and Save once the reviewer changes it", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "stance",
        value: "affirm",
        control: "enum",
        options: ["affirm", "reject"],
        open: true,
        status: pending,
      },
    });
    expect(wrapper.get("[data-primary-action]").text()).toMatch(/^Confirm/);
    await wrapper.get("select").setValue("reject");
    expect(wrapper.get("[data-primary-action]").text()).toMatch(/^Save/);
    wrapper.unmount();
  });

  it("treats a literal model placeholder 'no value' as an absence decision", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "speaker",
        value: "no value",
        control: "text",
        open: true,
        status: { status: "unresolved", method: "llm", derivation_method: "model" },
      },
    });
    expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("");
    expect(wrapper.get("[data-primary-action]").attributes("data-no-value-action")).toBeDefined();

    await wrapper.get("[data-no-value-action]").trigger("keydown", { key: "Enter" });

    expect(wrapper.emitted("noValue")).toEqual([[]]);
    expect(wrapper.emitted("save")).toBeUndefined();
    wrapper.unmount();
  });

  it("keeps an active typed draft mounted and focused through asynchronous field settlement", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      attachTo: document.body,
      props: {
        field: "speaker",
        value: "Jacques Derrida",
        control: "text",
        open: true,
        status: { status: "unresolved", method: "llm" },
      },
    });
    const editor = wrapper.get("textarea");
    (editor.element as HTMLTextAreaElement).focus();
    await editor.setValue("Reviewer draft");
    expect(document.activeElement).toBe(editor.element);

    await wrapper.setProps({
      open: false,
      value: "Background refresh",
      status: { status: "human_confirmed", method: "human" },
    });
    await nextTick();

    const stillEditing = wrapper.get("textarea");
    expect(stillEditing.element).toBe(editor.element);
    expect((stillEditing.element as HTMLTextAreaElement).value).toBe("Reviewer draft");
    expect(document.activeElement).toBe(editor.element);
    wrapper.unmount();
  });

  it("shows a model-proposed absence as a starred no-value state without filling the field", () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "speaker",
        value: null,
        control: "text",
        open: true,
        status: {
          status: "unresolved",
          method: "llm",
          evaluation_status: "no_supported_value",
          suggested_absence: true,
          confidence: 0.92,
        },
      },
    });
    expect(wrapper.get(".proposal").text()).toContain("★");
    expect(wrapper.get(".proposal").text()).toContain("No value");
    expect(wrapper.text()).not.toContain("[not established in source]");
    expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("");
    wrapper.unmount();
  });

  it("closes an optional edit on Cancel without saving", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: { field: "speaker", value: "Jacques Derrida", control: "text", status: {} },
    });
    await wrapper.get(".field-edit").trigger("click");
    expect(wrapper.find("textarea").exists()).toBe(true);
    const cancel = wrapper.findAll("button").find((b) => b.text() === "Cancel")!;
    await cancel.trigger("click");
    expect(wrapper.find("textarea").exists()).toBe(false);
    expect(wrapper.emitted("save")).toBeUndefined();
    wrapper.unmount();
  });
});
