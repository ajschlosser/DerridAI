// Copyright 2026 Aaron John Schlosser, PhD.
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
