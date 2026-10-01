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
    scholarly_effect: "advisory",
    phase: "find",
    effect_note: "candidates_not_evidence",
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
    scholarly_effect: "provenance_gate",
    phase: "validate",
    effect_note: "provenance_gate",
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
    const edgeBefore = wrapper.get(".diagram-edge").attributes("d");
    await node.trigger("pointerdown", { button: 0, pointerId: 2, clientX: 10, clientY: 10 });
    await node.trigger("pointermove", { pointerId: 2, clientX: 40, clientY: 25 });
    await node.trigger("pointerup", { pointerId: 2 });
    await flushPromises();
    const after = readPosition(node.attributes("style") || "");
    expect(after).toEqual({ left: before.left + 30, top: before.top + 15 });
    expect(wrapper.get(".diagram-edge").attributes("d")).not.toBe(edgeBefore);
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
    expect(wrapper.text()).not.toContain("Reset layout");
    expect(wrapper.find("[data-relation-resize-handle]").exists()).toBe(true);

    const openLayout = async () => {
      await wrapper.get(".ui-menu-trigger").trigger("click");
      await flushPromises();
      return wrapper.findAll('[role="menuitemradio"], [role="menuitem"]');
    };
    let items = await openLayout();
    expect(items.map((item) => item.text())).toEqual([
      "Horizontal",
      "Vertical",
      "Compact spacing",
      "Standard spacing",
      "Wide spacing",
      "Reset layout",
    ]);
    expect(items[0].attributes("aria-checked")).toBe("true");
    expect(items[5].attributes("role")).toBe("menuitem");
    await items[1].trigger("click");
    await flushPromises();

    items = await openLayout();
    expect(items[1].attributes("aria-checked")).toBe("true");
    expect(items[2].attributes("aria-checked")).toBe("true");
    await items[4].trigger("click");
    await flushPromises();
    items = await openLayout();
    expect(items[4].attributes("aria-checked")).toBe("true");
    expect(items[2].attributes("aria-checked")).toBe("false");
  });

  it("supports controlled stage selection", async () => {
    const wrapper = mount(PipelineGraphDiagram, {
      props: {
        stages,
        entryStageIds: ["retrieve"],
        strategies,
        title: "Pipeline",
        description: "Test pipeline",
        selectedStageId: "validate",
        showInspector: false,
      },
    });
    await flushPromises();
    const nodes = wrapper.findAll(".diagram-node");
    expect(nodes[1].classes()).toContain("selected");
    expect(wrapper.find(".stage-inspector").exists()).toBe(false);
    await nodes[0].trigger("click");
    expect(wrapper.emitted("update:selectedStageId")?.at(-1)).toEqual(["retrieve"]);
    // Still controlled: the parent has not accepted the change.
    expect(nodes[1].classes()).toContain("selected");
  });

  it("keeps unavailable and timeout fallback routes as separate edge kinds", async () => {
    const wrapper = mount(PipelineGraphDiagram, {
      props: {
        stages: [{ ...stages[0], on_unavailable: "validate", on_timeout: "validate" }, stages[1]],
        entryStageIds: ["retrieve"],
        strategies,
        title: "Pipeline",
        description: "Test pipeline",
      },
    });
    await flushPromises();

    expect(wrapper.find('[data-kind="on_unavailable"]').exists()).toBe(true);
    expect(wrapper.find('[data-kind="on_timeout"]').exists()).toBe(true);
    expect(wrapper.find(".diagram-legend [data-kind='on_unavailable']").exists()).toBe(true);
    expect(wrapper.find(".diagram-legend [data-kind='on_timeout']").exists()).toBe(true);
  });
});

describe("PipelineGraphDiagram edge type labels", () => {
  beforeEach(() => setActivePinia(createPinia()));

  const props = {
    stages,
    entryStageIds: ["retrieve"],
    strategies,
    title: "Pipeline",
    description: "Test pipeline",
  };

  it("labels the data type of edges touching the focused stage, and only then", async () => {
    const wrapper = mount(PipelineGraphDiagram, { props });
    await flushPromises();
    expect(wrapper.find(".diagram-edge-label").exists()).toBe(false);

    await wrapper.findAll(".diagram-node")[0].trigger("focus");
    const labels = wrapper.findAll(".diagram-edge-label");
    expect(labels.map((label) => label.text())).toEqual(["Candidate set"]);

    await wrapper.findAll(".diagram-node")[0].trigger("blur");
    expect(wrapper.find(".diagram-edge-label").exists()).toBe(false);
  });

  it("draws an ordering-only edge distinctly and says it carries no data", async () => {
    const wrapper = mount(PipelineGraphDiagram, {
      props: { ...props, orderingEdges: [{ from: "retrieve", to: "validate" }] },
    });
    await flushPromises();
    expect(wrapper.get(".diagram-edge").attributes("data-ordering")).toBe("true");
    expect(wrapper.get(".diagram-legend").text()).toContain("Runs first (no data)");
    await wrapper.findAll(".diagram-node")[1].trigger("focus");
    expect(wrapper.get(".diagram-edge-label").text()).toBe("Runs first (no data)");
  });

  it("shows no ordering styling for ordinary edges", async () => {
    const wrapper = mount(PipelineGraphDiagram, { props });
    await flushPromises();
    expect(wrapper.get(".diagram-edge").attributes("data-ordering")).toBeUndefined();
    expect(wrapper.get(".diagram-legend").text()).not.toContain("no data");
  });
});
