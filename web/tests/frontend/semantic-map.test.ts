/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
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
import * as runtime from "../../src/runtime/runtime.js";

vi.mock("../../src/runtime/runtime.js", () => ({
  navigateView: vi.fn(),
  openSemanticRecord: vi.fn(),
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

beforeEach(() => vi.clearAllMocks());

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

  it("clusters linked terms while compactly packing disconnected components", () => {
    const graph = buildSemanticMap([
      { id: "a", work: "A", concepts: ["trace", "writing"], topics: [], persons: [] },
      { id: "b", work: "B", concepts: ["trace", "writing"], topics: [], persons: [] },
      { id: "c", work: "C", concepts: ["ethics", "justice"], topics: [], persons: [] },
      { id: "d", work: "D", concepts: ["ethics", "justice"], topics: [], persons: [] },
    ]);
    const point = (label: string) => graph.nodes.find((node) => node.label === label)!;
    const distance = (left: ReturnType<typeof point>, right: ReturnType<typeof point>) =>
      Math.hypot(left.x - right.x, left.y - right.y);
    expect(distance(point("trace"), point("writing"))).toBeLessThan(
      distance(point("trace"), point("ethics")),
    );

    const denseDisconnected = buildSemanticMap(
      Array.from({ length: 10 }, (_, index) => ({
        id: `record-${index}`,
        work: `Work ${index}`,
        concepts: [`concept-${index}-a`, `concept-${index}-b`],
        topics: [],
        persons: [],
      })),
    );
    const xs = denseDisconnected.nodes.map((node) => node.x);
    const ys = denseDisconnected.nodes.map((node) => node.y);
    expect(Math.max(...xs) - Math.min(...xs)).toBeLessThan(1800);
    expect(Math.max(...ys) - Math.min(...ys)).toBeLessThan(1400);
  });

  it("balances per-Record term kinds instead of exhausting the budget on concepts", () => {
    const graph = buildSemanticMap([
      {
        id: "balanced",
        work: "Balanced",
        concepts: ["c1", "c2", "c3", "c4", "c5", "c6", "c7"],
        topics: ["topic-kept"],
        persons: ["person-kept"],
      },
    ]);
    expect(graph.nodes.map((node) => node.label)).toEqual(
      expect.arrayContaining(["topic-kept", "person-kept"]),
    );
  });

  it("weights repeated co-occurrences and distinguishes duplicate Record labels", () => {
    const graph = buildSemanticMap([
      {
        id: "record-alpha",
        work: "Shared Work",
        concepts: ["trace", "writing"],
        topics: [],
        persons: [],
      },
      {
        id: "record-beta",
        work: "Shared Work",
        concepts: ["trace", "writing"],
        topics: [],
        persons: [],
      },
    ]);
    const cooccurrence = graph.edges.find(
      (edge) => edge.source.includes("trace") && edge.target.includes("writing"),
    );
    expect(cooccurrence?.weight).toBe(2);
    const records = graph.nodes.filter((node) => node.kind === "record");
    expect(new Set(records.map((node) => node.label)).size).toBe(2);
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
    const layerStyle = wrapper.get("[data-semantic-map-layer]").attributes("style") || "";
    const zoom = Number(layerStyle.match(/scale\(([\d.]+)\)/)?.[1] || "1");
    await node.trigger("pointerdown", { button: 0, clientX: 10, clientY: 10, pointerId: 2 });
    await node.trigger("pointermove", { clientX: 30, clientY: 20, pointerId: 2 });
    await node.trigger("pointerup", { pointerId: 2 });
    const afterPointerDrag = read();
    expect(afterPointerDrag.left).toBeCloseTo(before.left + 20 / zoom, 5);
    expect(afterPointerDrag.top).toBeCloseTo(before.top + 10 / zoom, 5);

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

  it("keeps decluttered overview nodes visual but non-interactive", async () => {
    const graph = buildSemanticMap(
      Array.from({ length: 10 }, (_, index) => ({
        id: `record-${index}`,
        work: `Work ${index}`,
        concepts: [`concept ${index} alpha`, `concept ${index} beta`],
        topics: [`topic ${index}`],
        persons: [`Person ${index}`],
      })),
    );
    const wrapper = mount(SemanticMapCanvas, { props: { graph } });
    await flushPromises();

    const decluttered = wrapper.find(".semantic-map-node.decluttered");
    expect(decluttered.exists()).toBe(true);
    expect(decluttered.element.tagName).toBe("DIV");
    expect(decluttered.attributes("aria-hidden")).toBe("true");
  });

  it("changes spacing within clusters without multiplying the whole map by the old wide factor", async () => {
    const graph = buildSemanticMap(sources, "r1");
    const wrapper = mount(SemanticMapCanvas, { props: { graph } });
    await flushPromises();

    const width = () => {
      const style = wrapper.get("[data-semantic-map-layer]").attributes("style") || "";
      return Number(style.match(/width:\s*([\d.]+)px/)?.[1]);
    };
    const compactWidth = width();

    await wrapper.setProps({ density: "wide" });
    await flushPromises();
    const wideWidth = width();

    expect(wideWidth).toBeGreaterThanOrEqual(compactWidth);
    expect(wideWidth).toBeLessThan(compactWidth * 1.4);
  });
});

describe("SemanticMapFrame", () => {
  it("keeps placement and density controls in the View menu", async () => {
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
    expect(wrapper.get(".semantic-map-view-menu").text()).toContain("Wide spacing");
  });

  it("selects a Record for inspection before navigating to it", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", name: "record", component: { template: "<div/>" } }],
    });
    await router.push("/");
    const wrapper = mount(SemanticMapFrame, {
      props: { variant: "page", sources, focusId: "r1", showClose: false },
      global: { plugins: [router] },
    });
    await flushPromises();

    await wrapper.get('[data-relation-node-id="record:r1"]').trigger("click");
    expect(wrapper.find(".semantic-map-inspector").exists()).toBe(true);
    expect(runtime.openSemanticRecord).not.toHaveBeenCalled();

    await wrapper.get(".semantic-map-open-record").trigger("click");
    expect(runtime.openSemanticRecord).toHaveBeenCalledWith("r1");
  });

  it("filters by node kind and can focus the selected neighborhood", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", name: "record", component: { template: "<div/>" } }],
    });
    await router.push("/");
    const wrapper = mount(SemanticMapFrame, {
      props: { variant: "page", sources, focusId: "r1", showClose: false },
      global: { plugins: [router] },
    });
    await flushPromises();

    const personFilter = wrapper
      .findAll(".semantic-map-kind-filters button")
      .find((button) => button.text().toLowerCase().includes("person"));
    expect(personFilter).toBeTruthy();
    await personFilter!.trigger("click");
    expect(wrapper.find('[data-relation-node-id="person:rousseau"]').exists()).toBe(false);

    await wrapper.get('[data-relation-node-id="record:r1"]').trigger("click");
    await wrapper.get(".semantic-map-focus-action").trigger("click");
    expect(wrapper.text()).toContain("Show all");
  });
});
