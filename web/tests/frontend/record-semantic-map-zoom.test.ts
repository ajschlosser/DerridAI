// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import UiRelationViewport from "../../src/components/relations/UiRelationViewport.vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CorpusRecordSemanticMap from "../../src/components/corpus-builder/CorpusRecordSemanticMap.vue";

vi.mock("../../src/api/corpus", () => ({
  corpusBuildsApi: {
    recordSemanticMap: vi.fn(async () => ({
      version: 1,
      kind: "record_semantic_map",
      record_id: "r1",
      record_revision: 1,
      record_text_sha256: "x",
      layers: { document_intelligence: { status: "current" }, terms: { status: "current" } },
      mentions: [{ start: 0, end: 5, layer: "pos", tag: "NOUN", node_id: "" }],
      nodes: [
        { id: "a", label: "Alpha", type: "concept", local: true },
        { id: "b", label: "Beta", type: "concept", local: true },
      ],
      edges: [],
      linked_records: [],
      summary: {
        local_nodes: 2,
        shown_local_nodes: 2,
        neighbor_nodes: 0,
        in_record_edges: 0,
        outward_edges: 0,
        linked_records: 0,
      },
    })),
    semanticGraphNode: vi.fn(),
  },
}));

describe("record semantic map", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("scales node glyphs down as the map zooms in, and shows tags as tags", async () => {
    const wrapper = mount(CorpusRecordSemanticMap, {
      props: { buildId: "b1", record: { record_id: "r1", text: "Alpha beta" } },
    });
    await flushPromises();
    expect(wrapper.find(".mention-tag").text()).toBe("NOUN");
    const transform = () => wrapper.findAll("g.map-node")[1].attributes("transform");
    expect(transform()).toContain("scale(1)");
    const viewport = wrapper.findComponent(UiRelationViewport);
    viewport.vm.$emit("viewport-change", { pan: { x: 0, y: 0 }, zoom: 2 });
    await nextTick();
    expect(transform()).toContain("scale(0.5)");
    viewport.vm.$emit("viewport-change", { pan: { x: 0, y: 0 }, zoom: 0.5 });
    await nextTick();
    expect(transform()).toContain("scale(2)");
  });
});
