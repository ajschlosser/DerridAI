// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import RecordTraceabilityExplorer from "../../src/components/record/RecordTraceabilityExplorer.vue";

const graph = {
  specification_version: "1.0",
  root_id: "Record:r1",
  nodes: [
    {
      id: "Record:r1",
      object_type: "Record",
      object_id: "r1",
      label: "Record r1",
      materialization: "materialized",
    },
    {
      id: "SourceDocument:d1",
      object_type: "SourceDocument",
      object_id: "d1",
      label: "Document d1",
      materialization: "materialized",
    },
    {
      id: "FieldAssertion:a1",
      object_type: "FieldAssertion",
      object_id: "a1",
      label: "position_holder",
      materialization: "materialized",
    },
    {
      id: "SupportBinding:s1",
      object_type: "SupportBinding",
      object_id: "s1",
      label: "Support binding s1",
      materialization: "materialized",
    },
  ],
  edges: [
    {
      id: "d-r",
      source: "SourceDocument:d1",
      target: "Record:r1",
      relation: "contains record",
      inverse_relation: "belongs to document",
      normative: true,
      source_cardinality: "0..*",
      target_cardinality: "1",
    },
    {
      id: "r-a",
      source: "Record:r1",
      target: "FieldAssertion:a1",
      relation: "has assertion",
      inverse_relation: "assertion in context of",
      normative: true,
      source_cardinality: "0..*",
      target_cardinality: "1",
    },
    {
      id: "r-s",
      source: "Record:r1",
      target: "SupportBinding:s1",
      relation: "used by support binding",
      inverse_relation: "uses record",
      normative: false,
    },
  ],
};

const model = {
  specification_version: "1.0",
  nodes: [
    { type: "Record", label: "Record", profile: "Core", persistence: "durable", normative: true },
    {
      type: "SourceSpan",
      label: "Source span",
      profile: "Core",
      persistence: "durable_locator",
      normative: true,
    },
    {
      type: "FieldAssertion",
      label: "Field assertion",
      profile: "Core",
      persistence: "durable_when_retained",
      normative: true,
    },
  ],
  edges: [
    {
      id: "record_spans",
      source_type: "Record",
      target_type: "SourceSpan",
      relation: "derives from",
      inverse_relation: "contributes to",
      source_cardinality: "1..*",
      target_cardinality: "0..*",
      profile: "Core",
      normative: true,
    },
    {
      id: "record_assertions",
      source_type: "Record",
      target_type: "FieldAssertion",
      relation: "has assertion",
      inverse_relation: "assertion in context of",
      source_cardinality: "0..*",
      target_cardinality: "1",
      profile: "Core",
      normative: true,
    },
  ],
};

describe("RecordTraceabilityExplorer", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("lets the user choose among branches and re-centers on the chosen object", async () => {
    const wrapper = mount(RecordTraceabilityExplorer, { props: { graph } });

    expect(wrapper.get(".object-graph-focus").attributes("data-object-id")).toBe("Record:r1");
    expect(wrapper.findAll(".object-graph-neighbors li")).toHaveLength(3);

    await wrapper.get('button[data-object-id="FieldAssertion:a1"]').trigger("click");

    expect(wrapper.get(".object-graph-focus").attributes("data-object-id")).toBe(
      "FieldAssertion:a1",
    );
    expect(wrapper.text()).toContain("assertion in context of");
  });

  it("walks the normative model independently from the selected instance path", async () => {
    const wrapper = mount(RecordTraceabilityExplorer, { props: { graph, model } });

    const modeButtons = wrapper.findAll(".object-graph-modes button");
    await modeButtons[1].trigger("click");

    expect(wrapper.get(".object-graph-focus").attributes("data-object-id")).toBe("model:Record");
    expect(wrapper.findAll(".object-graph-neighbors li")).toHaveLength(2);

    await wrapper.get('button[data-object-id="model:SourceSpan"]').trigger("click");
    expect(wrapper.get(".object-graph-focus").attributes("data-object-id")).toBe(
      "model:SourceSpan",
    );
    expect(wrapper.text()).toContain("contributes to");
  });

  it("keeps traversal history separate from the graph and supports back navigation", async () => {
    const wrapper = mount(RecordTraceabilityExplorer, { props: { graph } });

    await wrapper.get('button[data-object-id="SourceDocument:d1"]').trigger("click");
    expect(wrapper.get(".object-graph-focus").attributes("data-object-id")).toBe(
      "SourceDocument:d1",
    );

    const historyButtons = wrapper.findAll(".object-graph-history-actions button");
    await historyButtons[0].trigger("click");

    expect(wrapper.get(".object-graph-focus").attributes("data-object-id")).toBe("Record:r1");
    expect(wrapper.findAll(".object-graph-neighbors li")).toHaveLength(3);
  });
});
