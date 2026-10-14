/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuildsApi = vi.hoisted(() => ({
  semanticContentGraphView: vi.fn(),
  semanticContentGraph: vi.fn(),
  rerunDocumentIntelligence: vi.fn(),
}));
vi.mock("../../src/api/corpus", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../src/api/corpus")>()),
  corpusBuildsApi,
}));
const intelligenceReads = vi.hoisted(() => ({ readDocumentIntelligence: vi.fn() }));
vi.mock("../../src/features/corpus-builder/api/documentIntelligenceReads", () => intelligenceReads);

import CorpusSemanticGraphPanel from "../../src/components/corpus-builder/CorpusSemanticGraphPanel.vue";
import { layoutGraph, nodeRadius } from "../../src/domain/semanticGraphLayout";

const node = (i: number, type = "concept") => ({
  id: `n${i}`,
  type,
  label: `Entity ${i}`,
  aliases: [],
  mention_count: 100 - i,
  record_count: 3,
  degree: 2,
});

function viewPayload(overrides: Record<string, unknown> = {}) {
  return {
    version: 1,
    kind: "semantic_content_graph_view",
    summary: { nodes: 12000, edges: 90000 },
    facets: {
      types: [
        { type: "concept", count: 9000 },
        { type: "person", count: 3000 },
      ],
      predicates: [],
    },
    query: {
      query: "",
      types: [],
      relation_kind: "all",
      focus: "",
      node_limit: 80,
      edge_limit: 400,
      min_mentions: 0,
    },
    view: {
      nodes: [node(1), node(2, "person"), node(3)],
      edges: [
        {
          id: "e1",
          source: "n1",
          target: "n2",
          predicate: "critiques",
          relation_kind: "semantic",
          authority_status: "disputed",
          count: 2,
        },
      ],
      candidate_nodes: 12000,
      candidate_edges: 90000,
      truncated_nodes: true,
      truncated_edges: true,
    },
    focus: null,
    index: {
      items: [node(1), node(2, "person")],
      total: 12000,
      offset: 0,
      limit: 50,
      sort: "mentions",
    },
    ...overrides,
  };
}

async function openPanel() {
  const wrapper = mount(CorpusSemanticGraphPanel, {
    props: { buildId: "b1", summary: { nodes: 12000, edges: 90000 } },
  });
  const details = wrapper.get("details");
  (details.element as HTMLDetailsElement).open = true;
  await details.trigger("toggle");
  await flushPromises();
  return wrapper;
}

describe("CorpusSemanticGraphPanel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    corpusBuildsApi.semanticContentGraphView.mockResolvedValue(viewPayload());
    intelligenceReads.readDocumentIntelligence.mockResolvedValue({ stale: false });
  });

  it("requests a bounded view instead of the whole graph and reports truncation", async () => {
    const wrapper = await openPanel();
    expect(corpusBuildsApi.semanticContentGraph).not.toHaveBeenCalled();
    const [buildId, params] = corpusBuildsApi.semanticContentGraphView.mock.calls[0];
    expect(buildId).toBe("b1");
    expect(params.node_limit).toBeLessThanOrEqual(250);
    expect(params.index_limit).toBe(50);
    expect(wrapper.findAll(".graph-node")).toHaveLength(3);
    expect(wrapper.find(".graph-banner.info").exists()).toBe(true);
    expect(wrapper.get(".graph-edge").classes()).toContain("disputed");
  });

  it("filters by entity type server-side through the facet chips", async () => {
    const wrapper = await openPanel();
    const chip = wrapper.findAll(".type-chip")[1];
    await chip.trigger("click");
    await flushPromises();
    expect(chip.attributes("aria-pressed")).toBe("true");
    const params = corpusBuildsApi.semanticContentGraphView.mock.calls.at(-1)![1];
    expect(params.types).toEqual(["person"]);
    expect(params.index_offset).toBe(0);
  });

  it("focuses an entity's neighbourhood and returns to the overview", async () => {
    const wrapper = await openPanel();
    corpusBuildsApi.semanticContentGraphView.mockResolvedValueOnce(
      viewPayload({
        focus: {
          node: node(2, "person"),
          relations: [
            {
              id: "e1",
              source: "n1",
              target: "n2",
              predicate: "critiques",
              relation_kind: "semantic",
              authority_status: "disputed",
              count: 2,
              direction: "incoming",
              other_id: "n1",
              other_label: "Entity 1",
              other_type: "concept",
              record_ids: ["r1"],
              record_count: 1,
              supporting_fields: ["position_holder"],
              derivation_method: "field_assertion_projection",
              evidence_ref_count: 1,
              observed_verbs: [],
            },
          ],
          relations_total: 1,
        },
      }),
    );
    await wrapper.findAll(".entity-index-table .entity-link")[1].trigger("click");
    await flushPromises();
    expect(corpusBuildsApi.semanticContentGraphView.mock.calls.at(-1)![1].focus).toBe("n2");
    expect(wrapper.get(".relation-list .badge").classes()).toContain("disputed");
    expect(wrapper.get(".breadcrumb [aria-current='page']").text()).toBe("Entity 2");
    await wrapper.get(".breadcrumb .crumb").trigger("click");
    await flushPromises();
    expect(corpusBuildsApi.semanticContentGraphView.mock.calls.at(-1)![1].focus).toBeUndefined();
  });

  it("pages the entity index", async () => {
    const wrapper = await openPanel();
    const next = wrapper.findAll(".pager button")[1];
    await next.trigger("click");
    await flushPromises();
    expect(corpusBuildsApi.semanticContentGraphView.mock.calls.at(-1)![1].index_offset).toBe(50);
  });

  it("uses one tab stop for the dense node set and roves focus with arrow keys", async () => {
    const wrapper = await openPanel();
    const graphNodes = wrapper.findAll(".graph-node");
    expect(graphNodes.filter((item) => item.attributes("tabindex") === "0")).toHaveLength(1);
    expect(graphNodes.filter((item) => item.attributes("tabindex") === "-1")).toHaveLength(
      graphNodes.length - 1,
    );

    const first = graphNodes[0];
    const second = graphNodes[1];
    await first.trigger("focus");
    await first.trigger("keydown", { key: "ArrowRight" });
    await flushPromises();

    expect(first.attributes("tabindex")).toBe("-1");
    expect(second.attributes("tabindex")).toBe("0");

    await second.trigger("keydown", { key: "Home" });
    await flushPromises();
    expect(first.attributes("tabindex")).toBe("0");
  });

  it("uses the shared relation viewport and keeps edges attached while nodes move", async () => {
    const wrapper = await openPanel();
    const viewport = wrapper.get(".graph-viewport");
    const layer = wrapper.get("[data-relation-viewport-layer]");
    const beforePan = layer.attributes("style") || "";

    await viewport.trigger("pointerdown", { button: 0, pointerId: 11, clientX: 20, clientY: 20 });
    await viewport.trigger("pointermove", { pointerId: 11, clientX: 65, clientY: 45 });
    await viewport.trigger("pointerup", { pointerId: 11 });
    expect(layer.attributes("style")).not.toBe(beforePan);

    const node = wrapper.findAll(".graph-node")[0];
    const beforeNode = node.attributes("transform");
    const edge = wrapper.get(".graph-edge");
    const beforeEdge = edge.attributes("d");

    await node.trigger("pointerdown", { button: 0, pointerId: 12, clientX: 10, clientY: 10 });
    await node.trigger("pointermove", { pointerId: 12, clientX: 38, clientY: 24 });
    await node.trigger("pointerup", { pointerId: 12 });
    await flushPromises();

    expect(node.attributes("transform")).not.toBe(beforeNode);
    expect(edge.attributes("d")).not.toBe(beforeEdge);

    const afterDrag = node.attributes("transform");
    await node.trigger("keydown", { key: "ArrowRight", altKey: true });
    await flushPromises();
    expect(node.attributes("transform")).not.toBe(afterDrag);

    expect(wrapper.text()).toContain("Reset graph layout");
    const handle = wrapper.get("[data-relation-resize-handle]");
    await handle.trigger("keydown", { key: "ArrowDown" });
    expect(viewport.attributes("style")).toContain("height:");
  });
});

describe("semantic graph layout", () => {
  it("is deterministic, stays in frame and pins the focus at the centre", () => {
    const nodes = Array.from({ length: 250 }, (_, i) => ({ id: `n${i}` }));
    const edges = nodes
      .slice(1)
      .map((n, i) => ({ source: `n${i % 10}`, target: n.id, weight: 1 + (i % 4) }));
    const started = performance.now();
    const a = layoutGraph(nodes, edges, { width: 960, height: 560, pinned: "n0" });
    expect(performance.now() - started).toBeLessThan(2000);
    const b = layoutGraph(nodes, edges, { width: 960, height: 560, pinned: "n0" });
    expect([...a.entries()]).toEqual([...b.entries()]);
    for (const point of a.values()) {
      expect(point.x).toBeGreaterThanOrEqual(0);
      expect(point.x).toBeLessThanOrEqual(960);
      expect(point.y).toBeGreaterThanOrEqual(0);
      expect(point.y).toBeLessThanOrEqual(560);
    }
    expect(nodeRadius(100, 100)).toBeGreaterThan(nodeRadius(1, 100));
  });
});
