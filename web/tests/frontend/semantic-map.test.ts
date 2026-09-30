/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import SemanticMapCanvas from "../../src/components/semantic/SemanticMapCanvas.vue";
import SemanticMapFrame from "../../src/components/semantic/SemanticMapFrame.vue";
import {
  buildSemanticMap,
  moveNode,
  panBy,
  type SemanticMapSource,
} from "../../src/domain/semanticMap";
import { useSemanticMapStore } from "../../src/stores/semanticMap";

vi.mock("../../src/runtime/runtime.js", () => ({
  navigateView: vi.fn(),
  listSemanticMapSources: vi.fn(() => ({ records: [], focusId: "" })),
}));

const sources: SemanticMapSource[] = [
  {
    id: "r1",
    work: "Of Grammatology",
    concepts: ["trace", "writing"],
    topics: ["presence"],
    persons: ["Rousseau"],
  },
  {
    id: "r2",
    work: "Writing and Difference",
    concepts: ["trace", "différance"],
    topics: ["presence"],
    persons: ["Levinas"],
  },
];

describe("semantic map layout", () => {
  it("links terms that occur together and keeps the layout stable", () => {
    const first = buildSemanticMap(sources, "r1");
    const second = buildSemanticMap(sources, "r1");
    expect(first.nodes.map((node) => node.label)).toEqual(
      expect.arrayContaining(["trace", "writing", "presence", "Rousseau", "Of Grammatology"]),
    );
    expect(
      first.edges.some((edge) => edge.source.includes("trace") && edge.target.includes("writing")),
    ).toBe(true);
    expect(first.nodes.map((node) => [node.id, node.x, node.y])).toEqual(
      second.nodes.map((node) => [node.id, node.x, node.y]),
    );
  });

  it("pans the map by the pointer delta and moves a term independently of that pan", () => {
    expect(panBy({ x: 10, y: 4 }, { x: 30, y: -8 })).toEqual({ x: 40, y: -4 });
    expect(moveNode({ x: 0, y: 0 }, { x: 20, y: 10 }, 2)).toEqual({ x: 10, y: 5 });
  });
});

describe("SemanticMapCanvas", () => {
  it("drags the map background", async () => {
    const graph = buildSemanticMap(sources, "r1");
    const wrapper = mount(SemanticMapCanvas, { props: { graph } });
    await flushPromises();
    const surface = wrapper.get(".semantic-map-canvas");
    const before = wrapper.get("[data-semantic-map-layer]").attributes("style") || "";
    await surface.trigger("pointerdown", { button: 0, clientX: 20, clientY: 40, pointerId: 1 });
    await surface.trigger("pointermove", { clientX: 70, clientY: 15, pointerId: 1 });
    await surface.trigger("pointerup", { pointerId: 1 });
    const after = wrapper.get("[data-semantic-map-layer]").attributes("style") || "";
    const read = (style: string) => {
      const match = style.match(/translate\(([-\d.]+)px,\s*([-.\d]+)px\)/);
      return { x: Number(match?.[1]), y: Number(match?.[2]) };
    };
    const start = read(before);
    const moved = read(after);
    expect(moved).toEqual({ x: start.x + 50, y: start.y - 25 });
  });

  it("drags and keyboard-nudges a node in graph space", async () => {
    const graph = buildSemanticMap(sources, "r1");
    const wrapper = mount(SemanticMapCanvas, { props: { graph } });
    await flushPromises();
    const node = wrapper.get(".semantic-map-node");
    const read = () => {
      const style = node.attributes("style") || "";
      const left = Number(style.match(/left:\s*([-.\d]+)px/)?.[1]);
      const top = Number(style.match(/top:\s*([-.\d]+)px/)?.[1]);
      return { left, top };
    };
    const before = read();
    await node.trigger("pointerdown", { button: 0, clientX: 10, clientY: 10, pointerId: 2 });
    await node.trigger("pointermove", { clientX: 30, clientY: 20, pointerId: 2 });
    await node.trigger("pointerup", { pointerId: 2 });
    expect(read()).toEqual({ left: before.left + 20, top: before.top + 10 });

    const afterDrag = read();
    await node.trigger("keydown", { key: "ArrowRight", altKey: true });
    expect(read()).toEqual({ left: afterDrag.left + 8, top: afterDrag.top });
  });

  it("supports keyboard resizing without turning the resize gesture into a pan", async () => {
    const graph = buildSemanticMap(sources, "r1");
    const wrapper = mount(SemanticMapCanvas, { props: { graph } });
    await flushPromises();
    const surface = wrapper.get(".semantic-map-canvas");
    const handle = wrapper.get("[data-relation-resize-handle]");
    await handle.trigger("keydown", { key: "ArrowDown" });
    expect(surface.attributes("style")).toContain("height: 252px");
  });
});

describe("SemanticMapFrame", () => {
  it("offers the four placements", async () => {
    const map = useSemanticMapStore();
    map.enable("record");
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", name: "record", component: { template: "<div/>" } }],
    });
    await router.push("/");
    const wrapper = mount(SemanticMapFrame, {
      props: { variant: "record", sources, focusId: "r1" },
      global: { plugins: [router] },
    });
    const choices = wrapper.findAll("[role='radio']").map((button) => button.text());
    expect(choices).toEqual(["Sidebar", "Above the record", "Large dialog", "Dedicated view"]);
    expect(wrapper.get("[role='radiogroup']").attributes("aria-label")).toBe(
      "Where to show the map",
    );
  });
});
