// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import PipelineGraphDiagram from "../../src/components/pipelines/PipelineGraphDiagram.vue";
import type { PipelineStage, PipelineStrategy } from "../../src/types/pipelines";

const stages: PipelineStage[] = [
  {
    id: "retrieve",
    strategy: "retrieve.chroma_similarity",
    enabled: true,
    config: {},
    next: ["validate"],
  },
  {
    id: "validate",
    strategy: "validate.provenance",
    enabled: true,
    config: {},
    next: [],
  },
];

const strategies: PipelineStrategy[] = [
  {
    strategy_id: "retrieve.chroma_similarity",
    version: 1,
    family: "candidate_generation",
    label: "Chroma semantic similarity",
    description: "Retrieve semantic candidates.",
    input_type: "query",
    output_type: "candidate_set",
    deterministic: false,
    invokes_llm: false,
    capabilities: [],
    config_schema: { type: "object", properties: {} },
  },
  {
    strategy_id: "validate.provenance",
    version: 1,
    family: "support_validation",
    label: "Provenance sufficiency gate",
    description: "Require source identity.",
    input_type: "candidate_set",
    output_type: "candidate_set",
    deterministic: true,
    invokes_llm: false,
    capabilities: [],
    config_schema: { type: "object", properties: {} },
  },
];

function readPosition(style: string) {
  return {
    left: Number(style.match(/left:\s*([-.\d]+)px/)?.[1]),
    top: Number(style.match(/top:\s*([-.\d]+)px/)?.[1]),
  };
}

describe("PipelineGraphDiagram relation interactions", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("pans the diagram background and drags a stage with live edge geometry", async () => {
    const wrapper = mount(PipelineGraphDiagram, {
      props: {
        stages,
        entryStageIds: ["retrieve"],
        strategies,
        title: "Pipeline",
        description: "Test pipeline",
      },
    });
    await flushPromises();

    const viewport = wrapper.get(".diagram-viewport");
    const layer = wrapper.get("[data-relation-viewport-layer]");
    const beforePan = layer.attributes("style") || "";
    await viewport.trigger("pointerdown", { button: 0, pointerId: 1, clientX: 20, clientY: 20 });
    await viewport.trigger("pointermove", { pointerId: 1, clientX: 70, clientY: 45 });
    await viewport.trigger("pointerup", { pointerId: 1 });
    expect(layer.attributes("style")).not.toBe(beforePan);

    const node = wrapper.findAll(".diagram-node")[0];
    const before = readPosition(node.attributes("style") || "");
    const edgeBefore = wrapper.get(".diagram-edges path").attributes("d");
    await node.trigger("pointerdown", { button: 0, pointerId: 2, clientX: 10, clientY: 10 });
    await node.trigger("pointermove", { pointerId: 2, clientX: 40, clientY: 25 });
    await node.trigger("pointerup", { pointerId: 2 });
    await flushPromises();
    const after = readPosition(node.attributes("style") || "");
    expect(after).toEqual({ left: before.left + 30, top: before.top + 15 });
    expect(wrapper.get(".diagram-edges path").attributes("d")).not.toBe(edgeBefore);
  });

  it("offers fit, reset, orientation, and resize controls", async () => {
    const wrapper = mount(PipelineGraphDiagram, {
      props: {
        stages,
        entryStageIds: ["retrieve"],
        strategies,
        title: "Pipeline",
        description: "Test pipeline",
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("Fit diagram");
    expect(wrapper.text()).toContain("Reset layout");
    expect(wrapper.get("[data-relation-resize-handle]").exists()).toBe(true);

    const vertical = wrapper
      .findAll(".diagram-controls button")
      .find((button) => button.text() === "Vertical");
    expect(vertical).toBeTruthy();
    await vertical!.trigger("click");
    expect(vertical!.attributes("aria-pressed")).toBe("true");
  });
});
