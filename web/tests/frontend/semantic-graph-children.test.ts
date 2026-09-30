// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import SemanticGraphEntityIndex from "../../src/components/corpus-builder/SemanticGraphEntityIndex.vue";
import SemanticGraphInspector from "../../src/components/corpus-builder/SemanticGraphInspector.vue";

const node = (i: number) => ({
  id: `n${i}`,
  type: "concept",
  label: `Entity ${i}`,
  aliases: [],
  mention_count: 10,
  record_count: 2,
  degree: 1,
});
const relation = (id: string, kind: "semantic" | "observational", status: string) => ({
  id,
  source: "n1",
  target: "n2",
  predicate: "co_occurs_with",
  relation_kind: kind,
  authority_status: status,
  count: 1,
  direction: "outgoing" as const,
  other_id: "n2",
  other_label: "Entity 2",
  other_type: "concept",
  record_ids: ["r1"],
  record_count: 1,
  supporting_fields: [],
  derivation_method: "x",
  evidence_ref_count: 0,
  observed_verbs: [],
});

beforeEach(() => setActivePinia(createPinia()));

describe("SemanticGraphInspector", () => {
  const base = {
    selectedNode: node(1),
    focusDetail: {
      node: node(1),
      relations: [
        relation("a", "semantic", "disputed"),
        relation("b", "observational", "unreviewed"),
      ],
      relations_total: 2,
    },
    selectedEdges: [],
    nodesById: new Map(),
    focusId: "",
    hueClass: () => "hue-1",
  };

  it("keeps semantic and observational relations in separate groups and shows disputed authority", () => {
    const wrapper = mount(SemanticGraphInspector, { props: base as never });
    expect(wrapper.findAll(".relation-group")).toHaveLength(2);
    expect(wrapper.findAll(".badge")).toHaveLength(1);
    expect(wrapper.get(".badge").classes()).toContain("disputed");
  });

  it("emits focus and clear instead of mutating parent state", async () => {
    const wrapper = mount(SemanticGraphInspector, { props: base as never });
    await wrapper.get(".focus-btn").trigger("click");
    await wrapper.get(".icon-btn").trigger("click");
    expect(wrapper.emitted("focus")![0]).toEqual(["n1", "Entity 1"]);
    expect(wrapper.emitted("clear")).toHaveLength(1);
  });

  it("shows the empty prompt without a selection", () => {
    const wrapper = mount(SemanticGraphInspector, {
      props: { ...base, selectedNode: null, focusDetail: null } as never,
    });
    expect(wrapper.find(".inspector-empty").exists()).toBe(true);
  });
});

describe("SemanticGraphEntityIndex", () => {
  const view = {
    summary: { nodes: 120 },
    index: { total: 120, offset: 0, items: [node(1), node(2)] },
  };

  it("emits focus for an entity and pages through the v-model offset", async () => {
    const wrapper = mount(SemanticGraphEntityIndex, {
      props: {
        index: view.index as never,
        nodeTotal: view.summary.nodes,
        loading: false,
        selectedNodeId: "n2",
        hueClass: () => "hue-1",
        sort: "mentions" as const,
        offset: 0,
        "onUpdate:offset": (value: number) => wrapper.setProps({ offset: value }),
      },
    });
    expect(wrapper.find("tr.selected").text()).toContain("Entity 2");
    await wrapper.findAll(".entity-link")[0].trigger("click");
    expect(wrapper.emitted("focus")![0]).toEqual(["n1", "Entity 1"]);
    await wrapper.findAll(".pager button")[1].trigger("click");
    expect(wrapper.props("offset")).toBe(50);
  });
});
