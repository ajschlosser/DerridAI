/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { corpusBuildsApi } from "../../src/api/corpus";
import * as intelligence from "../../src/features/corpus-builder/api/documentIntelligenceReads";
import CorpusSemanticWorkspace from "../../src/components/corpus-builder/CorpusSemanticWorkspace.vue";

describe("Semantic workspace", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("loads nothing until opened, then loads only the visible tab", async () => {
    const graph = vi.spyOn(corpusBuildsApi, "semanticContentGraphView").mockResolvedValue({
      version: 1,
      kind: "semantic_content_graph_view",
      summary: { nodes: 0, edges: 0 },
      facets: { types: [], predicates: [] },
      query: { query: "", types: [], relation_kind: "all", focus: "", node_limit: 80 },
      view: { nodes: [], edges: [], candidate_nodes: 0, candidate_edges: 0 },
      focus: null,
      index: { items: [], total: 0, offset: 0, limit: 50, sort: "mentions" },
    } as never);
    vi.spyOn(intelligence, "readDocumentIntelligence").mockResolvedValue(null as never);
    const aliases = vi
      .spyOn(corpusBuildsApi, "semanticAliases")
      .mockResolvedValue({ items: [], kinds: [] });
    const wrapper = mount(CorpusSemanticWorkspace, {
      props: { buildId: "b1", summary: { nodes: 3, edges: 2 } as never },
      attachTo: document.body,
    });
    expect(graph).not.toHaveBeenCalled();
    expect(aliases).not.toHaveBeenCalled();
    expect(document.body.querySelector("[role=dialog]")).toBeNull();

    await wrapper.find("button").trigger("click");
    await flushPromises();
    expect(document.body.querySelector("[role=dialog]")).not.toBeNull();
    expect(graph).toHaveBeenCalledTimes(1);
    expect(aliases).not.toHaveBeenCalled();

    const tabs = document.body.querySelectorAll<HTMLButtonElement>("[role=tab]");
    tabs[1].click();
    await flushPromises();
    expect(aliases).toHaveBeenCalledTimes(1);
    expect(graph).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });
});
