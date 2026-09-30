// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import RecordSemanticAnnotatedText from "../../src/components/corpus-builder/RecordSemanticAnnotatedText.vue";
import RecordSemanticMapLists from "../../src/components/corpus-builder/RecordSemanticMapLists.vue";
import { nodeTone, relationLabel } from "../../src/features/corpus-builder/domain/semanticMap";

beforeEach(() => setActivePinia(createPinia()));

const heidegger = { id: "person:h", label: "Heidegger", type: "person" };
const presence = { id: "concept:p", label: "presence", type: "concept" };

describe("RecordSemanticAnnotatedText", () => {
  const props = {
    text: "Heidegger questions presence.",
    idPrefix: "t",
    mentions: [
      { start: 0, end: 9, text: "Heidegger", layer: "ner", tag: "PERSON", node_id: heidegger.id },
      { start: 20, end: 28, text: "presence", layer: "pos", tag: "NOUN" },
    ],
  };

  it("keeps the text intact, links only mentions with a node, and emits the walk", async () => {
    const wrapper = mount(RecordSemanticAnnotatedText, { props });
    expect(wrapper.get(".annotated-text-body").text()).toContain(" questions ");
    expect(wrapper.findAll("button.mention")).toHaveLength(1);
    expect(wrapper.findAll("mark.mention")).toHaveLength(1);
    await wrapper.get("button.mention").trigger("click");
    expect(wrapper.emitted("walk")![0]).toEqual([heidegger.id, "Heidegger"]);
  });

  it("hides a layer's mentions without dropping their text", async () => {
    const wrapper = mount(RecordSemanticAnnotatedText, { props });
    await wrapper.get('[data-layer="ner"] input').setValue(false);
    expect(wrapper.findAll(".mention")).toHaveLength(1);
    expect(wrapper.get(".annotated-text-body").text()).toContain("Heidegger");
  });
});

describe("RecordSemanticMapLists", () => {
  it("lists shared records for a record step and emits navigation", async () => {
    const wrapper = mount(RecordSemanticMapLists, {
      props: {
        recordId: "r1",
        idPrefix: "t",
        neighborhood: null,
        map: {
          nodes: [
            { ...heidegger, local: true, record_count: 2 },
            { ...presence, local: true, record_count: 3 },
          ],
          linked_records: [
            {
              record_id: "r2",
              preview: "Presence again.",
              score: 1,
              shared_node_count: 2,
              shared_nodes: [heidegger, presence],
              shared_relation_ids: [],
            },
          ],
        } as never,
      },
    });
    expect(wrapper.findAll("dt").map((dt) => dt.text())).toEqual(["concept", "person"]);
    await wrapper.findAll(".record-links .btn")[0].trigger("click");
    await wrapper.findAll(".record-links .btn")[1].trigger("click");
    expect(wrapper.emitted("walkToRecord")![0]).toEqual(["r2"]);
    expect(wrapper.emitted("openRecord")![0]).toEqual(["r2"]);
  });

  it("does not offer to open the current record from an entity step", () => {
    const wrapper = mount(RecordSemanticMapLists, {
      props: {
        recordId: "r1",
        idPrefix: "t",
        map: null,
        neighborhood: {
          node: { ...heidegger, record_ids: ["r1"], record_count: 1 },
          nodes: [presence],
          edges: [
            {
              id: "e",
              source: heidegger.id,
              target: presence.id,
              predicate: "is_not_the_same_as",
              relation_kind: "semantic",
              authority_status: "disputed",
              record_ids: ["r1"],
            },
          ],
          total_edges: 1,
          records: [{ record_id: "r1", preview: "x" }],
          total_records: 1,
        } as never,
      },
    });
    expect(wrapper.get(".relation-list").text()).toContain("is not the same as");
    expect(wrapper.find(".record-link-actions .secondary").exists()).toBe(false);
  });
});

describe("semanticMap domain helpers", () => {
  it("maps entity types to tones and cleans predicates", () => {
    expect(nodeTone("character")).toBe("person");
    expect(nodeTone("unknown")).toBe("entity");
    expect(relationLabel({ predicate: "a_b" })).toBe("a b");
  });
});
