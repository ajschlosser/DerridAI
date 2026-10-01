// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import ResearchObjectDiagram from "../../src/components/record/ResearchObjectDiagram.vue";
import type { ResearchObjectEdge, ResearchObjectNode } from "../../src/types/researchObjectGraph";

const nodes: ResearchObjectNode[] = [
  {
    id: "SourceDocument:d1",
    object_type: "SourceDocument",
    object_id: "d1",
    label: "Of Grammatology",
    summary: "Jane Author",
    materialization: "materialized",
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
    id: "FieldAssertion:a1",
    object_type: "FieldAssertion",
    object_id: "a1",
    label: "position_holder",
    summary: "Levinas",
    materialization: "materialized",
  },
];

const edges: ResearchObjectEdge[] = [
  {
    id: "d-r",
    source: "SourceDocument:d1",
    target: "Record:r1",
    relation: "contains record",
    inverse_relation: "belongs to document",
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
];

function position(style: string) {
  return {
    left: Number(style.match(/left:\s*([-.\d]+)px/)?.[1]),
    top: Number(style.match(/top:\s*([-.\d]+)px/)?.[1]),
  };
}

describe("ResearchObjectDiagram relation interactions", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("renders ordinary HTML nodes rather than SVG foreignObject nodes", async () => {
    const wrapper = mount(ResearchObjectDiagram, {
      props: { nodes, edges, focusId: "Record:r1" },
    });
    await flushPromises();
    expect(wrapper.find("foreignObject").exists()).toBe(false);
    expect(wrapper.findAll("[data-relation-node]")).toHaveLength(nodes.length);
  });

  it("pans the background and moves nodes while rerouting edges", async () => {
    const wrapper = mount(ResearchObjectDiagram, {
      props: { nodes, edges, focusId: "Record:r1" },
    });
    await flushPromises();

    const viewport = wrapper.get(".diagram-viewport");
    const layer = wrapper.get("[data-relation-viewport-layer]");
    const beforePan = layer.attributes("style") || "";
    await viewport.trigger("pointerdown", { button: 0, pointerId: 1, clientX: 20, clientY: 20 });
    await viewport.trigger("pointermove", { pointerId: 1, clientX: 70, clientY: 45 });
    await viewport.trigger("pointerup", { pointerId: 1 });
    expect(layer.attributes("style")).not.toBe(beforePan);

    const node = wrapper.get("[data-object-id='Record:r1']");
    const before = position(node.attributes("style") || "");
    const edgeBefore = wrapper.findAll(".diagram-edge")[0].attributes("d");
    await node.trigger("pointerdown", { button: 0, pointerId: 2, clientX: 10, clientY: 10 });
    await node.trigger("pointermove", { pointerId: 2, clientX: 42, clientY: 26 });
    await node.trigger("pointerup", { pointerId: 2 });
    await flushPromises();

    expect(position(node.attributes("style") || "")).toEqual({
      left: before.left + 32,
      top: before.top + 16,
    });
    expect(wrapper.findAll(".diagram-edge")[0].attributes("d")).not.toBe(edgeBefore);
  });

  it("preserves focus activation and provides fit/reset/resize controls", async () => {
    const wrapper = mount(ResearchObjectDiagram, {
      props: { nodes, edges, focusId: "Record:r1" },
    });
    await flushPromises();

    const source = wrapper.get("[data-object-id='SourceDocument:d1']");
    await source.trigger("click");
    expect(wrapper.emitted("focus")?.at(-1)?.[0]).toBe("SourceDocument:d1");

    expect(wrapper.text()).toContain("Fit map");
    expect(wrapper.text()).toContain("Reset layout");
    const handle = wrapper.get("[data-relation-resize-handle]");
    await handle.trigger("keydown", { key: "ArrowDown" });
    expect(wrapper.get(".diagram-viewport").attributes("style")).toContain("height:");
  });

  it("supports keyboard node movement without changing domain data", async () => {
    const wrapper = mount(ResearchObjectDiagram, {
      props: { nodes, edges, focusId: "Record:r1" },
    });
    await flushPromises();
    const node = wrapper.get("[data-object-id='Record:r1']");
    const before = position(node.attributes("style") || "");
    await node.trigger("keydown", { key: "ArrowRight", altKey: true });
    await flushPromises();
    expect(position(node.attributes("style") || "")).toEqual({
      left: before.left + 8,
      top: before.top,
    });
    expect(nodes.find((item) => item.id === "Record:r1")).not.toHaveProperty("x");
  });
});
