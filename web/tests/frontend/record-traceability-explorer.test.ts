// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import RecordTraceabilityExplorer from "../../src/components/record/RecordTraceabilityExplorer.vue";
import ResearchObjectDiagram from "../../src/components/record/ResearchObjectDiagram.vue";

const graph = {
  specification_version: "1.0",
  root_id: "Record:r1",
  nodes: [
    {
      id: "SourceDocument:d1",
      object_type: "SourceDocument",
      object_id: "d1",
      label: "Of Grammatology",
      summary: "Jacques Derrida",
      materialization: "materialized",
    },
    {
      id: "SourceSpan:s1",
      object_type: "SourceSpan",
      object_id: "s1",
      label: "Source passage",
      summary: "Printed page 158",
      materialization: "embedded",
    },
    {
      id: "Record:r1",
      object_type: "Record",
      object_id: "r1",
      label: "Record r1",
      summary: "Of Grammatology · p. 158",
      materialization: "materialized",
    },
    {
      id: "RecordRevision:r1@3",
      object_type: "RecordRevision",
      object_id: "r1@3",
      label: "Revision 3",
      summary: "Current evidence-bearing state",
      materialization: "materialized",
    },
    {
      id: "FieldAssertion:a1",
      object_type: "FieldAssertion",
      object_id: "a1",
      label: "position_holder",
      summary: "Levinas",
      materialization: "materialized",
      status: "human_confirmed",
    },
    {
      id: "EvidenceRef:e1",
      object_type: "EvidenceRef",
      object_id: "e1",
      label: "Evidence reference e1",
      summary: "Record r1 · revision 3",
      materialization: "embedded",
    },
    {
      id: "SupportBinding:b1",
      object_type: "SupportBinding",
      object_id: "b1",
      label: "Support binding b1",
      summary: "supports",
      materialization: "materialized",
      status: "validated",
    },
    {
      id: "GeneratedClaim:c1",
      object_type: "GeneratedClaim",
      object_id: "c1",
      label: "Generated claim",
      summary: "Writing is not simply secondary to speech.",
      materialization: "materialized",
      status: "validated",
    },
    {
      id: "ResearchRun:run9",
      object_type: "ResearchRun",
      object_id: "run9",
      label: "Research run run9",
      summary: "Retained research operation",
      materialization: "reference",
    },
  ],
  edges: [
    {
      id: "d-s",
      source: "SourceDocument:d1",
      target: "SourceSpan:s1",
      relation: "contains span",
      inverse_relation: "belongs to document",
      normative: true,
    },
    {
      id: "d-r",
      source: "SourceDocument:d1",
      target: "Record:r1",
      relation: "contains record",
      inverse_relation: "belongs to document",
      normative: true,
    },
    {
      id: "r-s",
      source: "Record:r1",
      target: "SourceSpan:s1",
      relation: "derives from",
      inverse_relation: "contributes to",
      normative: true,
    },
    {
      id: "r-rev",
      source: "Record:r1",
      target: "RecordRevision:r1@3",
      relation: "has revision",
      inverse_relation: "revision of",
      normative: true,
    },
    {
      id: "r-a",
      source: "Record:r1",
      target: "FieldAssertion:a1",
      relation: "has assertion",
      inverse_relation: "assertion in context of",
      normative: true,
    },
    {
      id: "e-rev",
      source: "EvidenceRef:e1",
      target: "RecordRevision:r1@3",
      relation: "locates revision",
      inverse_relation: "referenced by evidence",
      normative: true,
    },
    {
      id: "b-e",
      source: "SupportBinding:b1",
      target: "EvidenceRef:e1",
      relation: "binds evidence",
      inverse_relation: "bound by",
      normative: true,
    },
    {
      id: "c-b",
      source: "GeneratedClaim:c1",
      target: "SupportBinding:b1",
      relation: "has support binding",
      inverse_relation: "binds claim",
      normative: true,
    },
    {
      id: "run-c",
      source: "ResearchRun:run9",
      target: "GeneratedClaim:c1",
      relation: "contains generated claim",
      inverse_relation: "generated in research run",
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

  it("orients the researcher with a bounded, task-based trace instead of an endless path", () => {
    const wrapper = mount(RecordTraceabilityExplorer, { props: { graph, model } });

    expect(wrapper.text()).toContain("Trace this record");
    expect(wrapper.text()).toContain("Bounded record trace");
    expect(wrapper.text()).toContain("9 objects · 9 relationships");
    expect(wrapper.text()).toContain("Where it came from");
    expect(wrapper.text()).toContain("How metadata was established");
    expect(wrapper.text()).toContain("How it was later used");
    expect(wrapper.find(".object-graph-history").exists()).toBe(false);
  });

  it("changes focus without extending or duplicating the graph", async () => {
    const wrapper = mount(RecordTraceabilityExplorer, { props: { graph, model } });

    expect(wrapper.text()).toContain("Corpus record");
    await wrapper.get('button[data-object-id="FieldAssertion:a1"]').trigger("click");

    expect(wrapper.text()).toContain("Metadata assertion");
    expect(wrapper.text()).toContain(
      "A metadata value together with how it was derived, evaluated, and reviewed.",
    );
    expect(wrapper.text()).toContain("1 direct connections");

    await wrapper.get('button[data-object-id="Record:r1"]').trigger("click");
    expect(wrapper.text()).toContain("Corpus record");
    expect(wrapper.text()).toContain("9 objects · 9 relationships");
  });

  it("separates the actual record trace from the normative DERRIDAI model", async () => {
    const wrapper = mount(RecordTraceabilityExplorer, { props: { graph, model } });

    const modelTab = wrapper
      .findAll('[role="tab"]')
      .find((button) => button.text().includes("DERRIDAI model"));
    expect(modelTab).toBeTruthy();
    await modelTab!.trigger("click");

    expect(wrapper.text()).toContain("Explore the DERRIDAI model");
    expect(wrapper.text()).toContain("Normative model");
    expect(wrapper.text()).toContain("3 objects · 2 relationships");
    expect(wrapper.text()).toContain("This is the finite DERRIDAI 1.0 relationship model.");
  });
});

describe("ResearchObjectDiagram", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("renders the retained graph visually and lets a node become the selected focus", async () => {
    const wrapper = mount(ResearchObjectDiagram, {
      props: {
        nodes: graph.nodes,
        edges: graph.edges,
        focusId: "Record:r1",
      },
    });

    expect(wrapper.find("svg.diagram-canvas").exists()).toBe(true);
    expect(wrapper.findAll(".diagram-node")).toHaveLength(graph.nodes.length);
    expect(wrapper.findAll(".diagram-edge")).toHaveLength(graph.edges.length);
    expect(wrapper.get('button[data-object-id="Record:r1"]').attributes("aria-pressed")).toBe(
      "true",
    );

    await wrapper.get('button[data-object-id="EvidenceRef:e1"]').trigger("click");
    expect(wrapper.emitted("focus")?.at(-1)).toEqual(["EvidenceRef:e1"]);
  });

  it("visually distinguishes application-specific links from normative relationships", () => {
    const wrapper = mount(ResearchObjectDiagram, {
      props: {
        nodes: graph.nodes,
        edges: graph.edges,
        focusId: "GeneratedClaim:c1",
      },
    });

    expect(wrapper.findAll(".diagram-edge.application")).toHaveLength(1);
    expect(wrapper.findAll(".diagram-edge.active").length).toBeGreaterThan(0);
  });
});
