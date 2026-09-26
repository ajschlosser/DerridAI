// Copyright 2026 Aaron John Schlosser, PhD.
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

  it("waits for a save in flight before moving focus", async () => {
    // As the workspace does, the save marks its field as saving the moment the panel emits it.
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

  it("closes an optional edit on Cancel without saving", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: { field: "speaker", value: "Jacques Derrida", control: "text", status: {} },
    });
    await wrapper.get(".field-edit").trigger("click");
    expect(wrapper.find("input").exists()).toBe(true);
    const cancel = wrapper.findAll("button").find((b) => b.text() === "Cancel")!;
    await cancel.trigger("click");
    expect(wrapper.find("input").exists()).toBe(false);
    expect(wrapper.emitted("save")).toBeUndefined();
    wrapper.unmount();
  });
});
