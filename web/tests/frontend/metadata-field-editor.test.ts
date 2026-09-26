import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";
import CorpusMetadataFieldEditor from "../../src/components/CorpusMetadataFieldEditor.vue";
import { normalizeMetadataFieldValue } from "../../src/domain/metadataFieldRegistry";

const stanceOptions = [
  "affirm",
  "reject",
  "criticize",
  "question",
  "qualify",
  "suspend",
  "neutral",
  "describe",
];

describe("CorpusMetadataFieldEditor auto-population", () => {
  it("selects a confident stance proposal when the record value arrives progressively", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "stance",
        value: "",
        control: "enum",
        options: stanceOptions,
        open: true,
        status: { status: "unresolved", method: "llm", confidence: 0.4, auto_populated: false },
      },
    });
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("");

    await wrapper.setProps({
      value: "affirm",
      status: {
        status: "model_inferred",
        method: "llm",
        confidence: 0.91,
        auto_populated: true,
        proposed_value: "affirm",
        llm_checked: true,
      },
    });
    await nextTick();
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("affirm");
    wrapper.unmount();
  });

  it("normalizes direct grammatical stance aliases so older model output still selects an enum option", async () => {
    expect(normalizeMetadataFieldValue("stance", "affirmed")).toBe("affirm");
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "stance",
        value: "",
        control: "enum",
        options: stanceOptions,
        open: true,
        status: {
          status: "model_inferred",
          method: "llm",
          confidence: 0.92,
          auto_populated: true,
          proposed_value: "affirmed",
          raw_llm_value: "affirmed",
        },
      },
    });
    await nextTick();
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("affirm");
    wrapper.unmount();
  });

  it("keeps reviewer-defined deterministic region selected during an LLM disagreement", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "region_type",
        value: "main_text",
        control: "enum",
        options: ["front_matter", "main_text", "back_matter"],
        open: true,
        status: {
          status: "unresolved",
          method: "deterministic+llm",
          reason_code: "deterministic_llm_disagreement",
          deterministic_value: "main_text",
          llm_value: "front_matter",
          llm_confidence: 0.96,
          prefilled_candidate: "deterministic",
          llm_checked: true,
        },
      },
    });
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("main_text");
    wrapper.unmount();
  });

  it("deduplicates option suggestions for multi-value metadata fields", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "concepts",
        value: "",
        control: "multi-combobox",
        options: ["cities of refuge", "cities of refuge", "hospitality", "cities of refuge"],
        open: true,
        status: { status: "model_inferred", method: "llm", confidence: 0.82, auto_populated: true },
      },
    });

    await nextTick();
    const values = [...wrapper.findAll("datalist option")].map((option) =>
      option.attributes("value"),
    );
    expect(values).toEqual(["cities of refuge", "hospitality"]);
    wrapper.unmount();
  });

  it("does not expose a leaked field assessment as a topic value", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "topics",
        value: "confidence: null, needs_review: true, reason: No text could be used as evidence.",
        control: "multi-combobox",
        open: true,
        status: {
          status: "unresolved",
          method: "llm",
          confidence: null,
          proposed_value: [],
          reason: "No text could be used as evidence.",
        },
      },
    });
    expect((wrapper.get("input").element as HTMLInputElement).value).toBe("");
    wrapper.unmount();
  });

  it("identifies a required empty LLM result as LLM provenance rather than unclassified", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "speaker",
        value: null,
        control: "text",
        open: true,
        status: {
          status: "unresolved",
          method: "hybrid",
          value_source: "llm",
          verification_status: "pending_review",
          reason_code: "ambiguous",
        },
      },
    });
    expect(wrapper.text()).toContain("LLM source");
    expect(wrapper.text()).toContain("Needs review");
    wrapper.unmount();
  });

  it("allows adding multiple unique values from the autocomplete list", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "concepts",
        value: "cities of refuge",
        control: "multi-combobox",
        options: ["cities of refuge", "hospitality", "cosmopolitanism"],
        open: true,
        status: { status: "model_inferred", method: "llm", confidence: 0.72, auto_populated: true },
      },
    });
    const input = wrapper.get("input");
    await input.setValue("cities of refuge, hospitality");
    await input.trigger("change");
    await nextTick();
    expect((wrapper.get("input").element as HTMLInputElement).value).toBe(
      "cities of refuge, hospitality",
    );
    wrapper.unmount();
  });

  it("keeps canonical FieldAssertion provenance editable", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "speaker",
        value: "Jacques Derrida",
        control: "text",
        status: {
          status: "model_inferred",
          method: "llm",
          assertion_id: "assertion-1",
          field_id: "derridai.speaker",
          derivation_method: "model",
          evaluation_status: "value_supported",
          authority_status: "unreviewed",
          value_status: "present",
        },
      },
    });

    expect(wrapper.find("input").exists()).toBe(false);
    const edit = wrapper.findAll("button").find((button) => button.text().includes("Edit"));
    expect(edit).toBeTruthy();
    await edit!.trigger("click");
    await nextTick();
    expect(wrapper.find("input").exists()).toBe(true);
    expect((wrapper.get("input").element as HTMLInputElement).value).toBe("Jacques Derrida");
    expect(wrapper.find(".assertion-provenance").exists()).toBe(true);
    wrapper.unmount();
  });

  it("unwraps structured compatibility values instead of rendering object Object", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "speaker",
        value: { value: "Jacques Derrida", reason: "model proposal" },
        control: "text",
        status: { status: "model_inferred", method: "llm" },
      },
    });

    expect(wrapper.text()).toContain("Jacques Derrida");
    expect(wrapper.text()).not.toContain("[object Object]");
    const edit = wrapper.findAll("button").find((button) => button.text().includes("Edit"));
    await edit!.trigger("click");
    await nextTick();
    expect((wrapper.get("input").element as HTMLInputElement).value).toBe("Jacques Derrida");
    wrapper.unmount();
  });
});

describe("CorpusMetadataFieldEditor memory hints", () => {
  it("offers less certain earlier values as chips that fill the draft, and labels namespaced derivations", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: {
        field: "stance",
        value: "",
        control: "enum",
        options: stanceOptions,
        open: true,
        status: {
          status: "model_inferred",
          derivation_method: "derridai:memory",
          assertion_id: "a1",
          confidence: 0.8,
        },
        hints: [{ value: "criticize", similarity: 0.81, support: 1 }],
      },
    });
    expect(wrapper.get(".memory-hints").text()).toContain("81%");
    await wrapper.get(".hint-chip").trigger("click");
    await nextTick();
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("criticize");
    expect(wrapper.text()).toContain("Metadata memory");
    expect(wrapper.text()).not.toContain("LLM source");
  });

  it("shows no hint strip when there are none", () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: { field: "stance", value: "", control: "enum", options: stanceOptions, open: true },
    });
    expect(wrapper.find(".memory-hints").exists()).toBe(false);
  });
});
