import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CorpusMetadataFieldEditor from "../../src/components/CorpusMetadataFieldEditor.vue";
import LlmExecutionControl from "../../src/components/LlmExecutionControl.vue";
import UiCombobox from "../../src/components/ui/UiCombobox.vue";

vi.mock("../../src/api/system", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../src/api/system")>();
  return {
    ...actual,
    systemApi: {
      ...actual.systemApi,
      researcherProviderStatus: vi.fn(async () => ({ models: [{ name: "qwen3.5:4b" }] })),
    },
  };
});

const stance = ["affirm", "reject", "criticize", "question", "qualify"];

describe("model-suggested values", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("leads a combobox list with the model's value and marks it in words", async () => {
    const wrapper = mount(UiCombobox, {
      attachTo: document.body,
      props: { modelValue: "", label: "Concept", options: ["a", "b", "c"], recommended: ["c"] },
    });
    await wrapper.get("input").trigger("focus");
    await wrapper.vm.$nextTick();
    const items = Array.from(document.body.querySelectorAll('[role="option"]'));
    expect(items.map((item) => item.querySelector(".combo-option-text")?.textContent)).toEqual([
      "c",
      "a",
      "b",
    ]);
    expect(items[0].getAttribute("data-recommended")).toBe("true");
    expect(items[0].textContent).toContain("Suggested");
    expect(items[1].getAttribute("data-recommended")).toBeNull();
    wrapper.unmount();
  });

  it("groups the model's enum proposal first, then every value", () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "stance",
        value: "",
        control: "enum",
        options: stance,
        open: true,
        status: {
          status: "model_inferred",
          method: "llm",
          confidence: 0.9,
          llm_value: "criticize",
        },
      },
    });
    const groups = wrapper.findAll("optgroup");
    expect(groups).toHaveLength(2);
    expect(groups[0].findAll("option").map((option) => option.attributes("value"))).toEqual([
      "criticize",
    ]);
    expect(groups[0].text()).toContain("Suggested");
    // Nothing is lost or duplicated: the rest follow, in their own order.
    expect(groups[1].findAll("option").map((option) => option.attributes("value"))).toEqual([
      "affirm",
      "reject",
      "question",
      "qualify",
    ]);
  });

  it("keeps a plain list when the model proposed nothing", () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: { field: "stance", value: "", control: "enum", options: stance, open: true },
    });
    expect(wrapper.findAll("optgroup")).toHaveLength(0);
    expect(wrapper.findAll("select option").length).toBeGreaterThanOrEqual(stance.length);
  });
});

describe("LlmExecutionControl", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("loads the model choices when the profile arrives after its id was already selected", async () => {
    const wrapper = mount(LlmExecutionControl, {
      props: { modelValue: "local", profiles: [] },
    });
    await flushPromises();
    expect(wrapper.find("datalist option").exists()).toBe(false);
    await wrapper.setProps({
      profiles: [{ id: "local", name: "Local", type: "ollama", base_url: "http://x", model: "" }],
    });
    await flushPromises();
    expect(wrapper.findAll("datalist option").map((o) => o.attributes("value"))).toEqual([
      "qwen3.5:4b",
    ]);
  });
});

describe("evidence selection preview", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("shows the text selected in the record and keeps it until it is used", async () => {
    const record = document.createElement("div");
    record.setAttribute("data-record-text", "");
    record.textContent = "Responsibility precedes freedom.";
    document.body.appendChild(record);
    const wrapper = mount(CorpusMetadataFieldEditor, {
      attachTo: document.body,
      props: { field: "concept", value: "responsibility", control: "text", open: true },
    });
    expect(wrapper.get(".selection-preview").attributes("data-state")).toBe("empty");
    const range = document.createRange();
    range.selectNodeContents(record);
    window.getSelection()?.removeAllRanges();
    window.getSelection()?.addRange(range);
    document.dispatchEvent(new Event("selectionchange"));
    await wrapper.vm.$nextTick();
    expect(wrapper.get(".selection-preview").text()).toContain("Responsibility precedes freedom.");
    // A selection elsewhere on the page is not the record's text and is ignored.
    window.getSelection()?.removeAllRanges();
    await wrapper.get(".field-tools .link-button:nth-last-child(2)").trigger("click");
    expect(wrapper.emitted("saveWithSelectionEvidence")?.at(-1)?.[1]).toBe(
      "Responsibility precedes freedom.",
    );
    expect(wrapper.get(".selection-preview").attributes("data-state")).toBe("empty");
    wrapper.unmount();
    record.remove();
  });
});
