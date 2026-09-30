/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuildsApi = vi.hoisted(() => ({
  recordSemanticMap: vi.fn(),
  semanticGraphNode: vi.fn(),
  rerunDocumentIntelligence: vi.fn(),
}));

vi.mock("../../src/api/corpus", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/corpus")>("../../src/api/corpus");
  return { ...actual, corpusBuildsApi };
});

import CorpusRecordSemanticMap from "../../src/components/corpus-builder/CorpusRecordSemanticMap.vue";

const text = "Heidegger questions presence.";
const heidegger = { id: "person:h", label: "Heidegger", type: "person" };
const presence = { id: "concept:p", label: "presence", type: "concept" };

function recordMap(recordId: string, termsStatus = "ok") {
  return {
    version: 1,
    kind: "record_semantic_map",
    record_id: recordId,
    record_revision: 1,
    record_text_sha256: "x",
    layers: { document_intelligence: { status: "missing" }, terms: { status: termsStatus } },
    mentions:
      recordId === "r1"
        ? [
            {
              start: 0,
              end: 9,
              text: "Heidegger",
              layer: "ner",
              tag: "PERSON",
              node_id: heidegger.id,
            },
          ]
        : [],
    nodes: [
      { ...heidegger, local: true, record_count: 2 },
      { ...presence, local: true, record_count: 3 },
    ],
    edges: [
      {
        id: "rel:1",
        source: heidegger.id,
        target: presence.id,
        predicate: "questions",
        relation_kind: "semantic",
        in_record: true,
        record_ids: [recordId],
      },
    ],
    linked_records: [
      {
        record_id: "r2",
        preview: "Presence again, with Heidegger.",
        score: 1.2,
        shared_node_count: 2,
        shared_nodes: [heidegger, presence],
        shared_relation_ids: [],
      },
    ],
    summary: {
      local_nodes: 2,
      shown_local_nodes: 2,
      neighbor_nodes: 0,
      in_record_edges: 1,
      outward_edges: 0,
      linked_records: 1,
    },
  };
}

function neighborhood() {
  return {
    version: 1,
    kind: "semantic_node_neighborhood",
    node: { ...heidegger, record_ids: ["r1", "r2"], record_count: 2 },
    nodes: [{ ...presence, record_count: 3 }],
    edges: [
      {
        id: "rel:1",
        source: heidegger.id,
        target: presence.id,
        predicate: "questions",
        relation_kind: "semantic",
        authority_status: "unreviewed",
        record_ids: ["r1"],
      },
    ],
    total_edges: 1,
    records: [
      { record_id: "r1", preview: text },
      { record_id: "r2", preview: "Presence again, with Heidegger." },
    ],
    total_records: 2,
  };
}

function mountMap() {
  return mount(CorpusRecordSemanticMap, {
    props: { buildId: "b1", record: { record_id: "r1", text, record_revision: 1 } },
  });
}

describe("CorpusRecordSemanticMap", () => {
  beforeEach(() => {
    corpusBuildsApi.recordSemanticMap.mockReset();
    corpusBuildsApi.semanticGraphNode.mockReset();
    corpusBuildsApi.rerunDocumentIntelligence.mockReset();
    corpusBuildsApi.recordSemanticMap.mockImplementation(async (_build: string, id: string) =>
      recordMap(id),
    );
    corpusBuildsApi.semanticGraphNode.mockResolvedValue(neighborhood());
  });

  it("shows the record's annotated text, nodes and linked records", async () => {
    const wrapper = mountMap();
    await flushPromises();
    expect(corpusBuildsApi.recordSemanticMap).toHaveBeenCalledWith("b1", "r1");
    const mention = wrapper.get("button.mention");
    expect(mention.text()).toContain("Heidegger");
    expect(mention.attributes("data-layer")).toBe("ner");
    expect(
      wrapper
        .get(".annotated-text-body")
        .text()
        .replace(/PERSON/, ""),
    ).toBe(text);
    expect(wrapper.findAll(".map-node[role='button']")).toHaveLength(2);
    expect(wrapper.get(".record-links").text()).toContain("r2");
  });

  it("walks from a mention to a node, on to a linked record, and back along the trail", async () => {
    const wrapper = mountMap();
    await flushPromises();
    await wrapper.get("button.mention").trigger("click");
    await flushPromises();
    expect(corpusBuildsApi.semanticGraphNode).toHaveBeenCalledWith("b1", heidegger.id);
    expect(wrapper.get(".node-step-head h4").text()).toBe("Heidegger");
    expect(wrapper.get(".relation-list").text()).toContain("questions");

    const explore = wrapper
      .findAll(".record-links li")
      .find((item) => item.text().includes("r2"))!
      .findAll("button")[0];
    await explore.trigger("click");
    await flushPromises();
    expect(corpusBuildsApi.recordSemanticMap).toHaveBeenLastCalledWith("b1", "r2");
    expect(wrapper.findAll(".semantic-map-trail li")).toHaveLength(3);
    // Another record's map has no text to annotate here; it can be opened in review instead.
    expect(wrapper.find(".annotated-text").exists()).toBe(false);
    await wrapper.get(".record-step-actions button").trigger("click");
    expect(wrapper.emitted("openRecord")).toEqual([["r2"]]);

    await wrapper.get(".semantic-map-trail > button").trigger("click");
    expect(wrapper.get(".node-step-head h4").text()).toBe("Heidegger");
    await wrapper.findAll(".trail-step")[0].trigger("click");
    expect(wrapper.find(".semantic-map-trail").exists()).toBe(false);
    expect(corpusBuildsApi.recordSemanticMap).toHaveBeenCalledTimes(2); // cached, not refetched
  });

  it("starts again when the record text changes, and offers reanalysis for stale layers", async () => {
    corpusBuildsApi.recordSemanticMap.mockImplementation(async (_build: string, id: string) =>
      recordMap(id, "stale"),
    );
    corpusBuildsApi.rerunDocumentIntelligence.mockResolvedValue({});
    const wrapper = mountMap();
    await flushPromises();
    expect(wrapper.find(".semantic-map-status.warning").exists()).toBe(true);
    await wrapper.get(".semantic-map-layers button").trigger("click");
    await flushPromises();
    expect(corpusBuildsApi.rerunDocumentIntelligence).toHaveBeenCalledWith("b1");
    expect(corpusBuildsApi.recordSemanticMap).toHaveBeenCalledTimes(2);
    expect(wrapper.emitted("refreshed")).toHaveLength(1);

    await wrapper.setProps({
      record: { record_id: "r1", text: `${text} Edited.`, record_revision: 2 },
    });
    await flushPromises();
    expect(corpusBuildsApi.recordSemanticMap).toHaveBeenCalledTimes(3);
  });
  it("uses the shared draggable, zoomable, resizable relation viewport", async () => {
    const wrapper = mountMap();
    await flushPromises();

    const viewport = wrapper.get(".semantic-map-viewport");
    const layer = wrapper.get("[data-relation-viewport-layer]");
    const beforePan = layer.attributes("style") || "";
    await viewport.trigger("pointerdown", { button: 0, pointerId: 4, clientX: 20, clientY: 20 });
    await viewport.trigger("pointermove", { pointerId: 4, clientX: 65, clientY: 40 });
    await viewport.trigger("pointerup", { pointerId: 4 });
    expect(layer.attributes("style")).not.toBe(beforePan);

    const node = wrapper.findAll(".map-node[role='button']")[0];
    const beforeTransform = node.attributes("transform");
    const edge = wrapper.findAll(".map-edge")[0];
    const beforeEdge = [edge.attributes("x1"), edge.attributes("y1"), edge.attributes("x2"), edge.attributes("y2")];

    await node.trigger("pointerdown", { button: 0, pointerId: 5, clientX: 10, clientY: 10 });
    await node.trigger("pointermove", { pointerId: 5, clientX: 30, clientY: 25 });
    await node.trigger("pointerup", { pointerId: 5 });
    await flushPromises();

    expect(node.attributes("transform")).not.toBe(beforeTransform);
    expect([
      edge.attributes("x1"),
      edge.attributes("y1"),
      edge.attributes("x2"),
      edge.attributes("y2"),
    ]).not.toEqual(beforeEdge);

    const afterDrag = node.attributes("transform");
    await node.trigger("keydown", { key: "ArrowRight", altKey: true });
    await flushPromises();
    expect(node.attributes("transform")).not.toBe(afterDrag);

    expect(wrapper.text()).toContain("Reset map layout");
    const handle = wrapper.get("[data-relation-resize-handle]");
    await handle.trigger("keydown", { key: "ArrowDown" });
    expect(viewport.attributes("style")).toContain("height:");
  });

});
