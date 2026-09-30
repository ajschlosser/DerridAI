/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { RecordSemanticMap, SemanticNodeNeighborhood } from "../../api/corpus";
import RecordSemanticMapLists from "./RecordSemanticMapLists.vue";

const heidegger = { id: "person:heidegger", label: "Heidegger", type: "person" };
const presence = { id: "concept:presence", label: "presence", type: "concept" };

const map = {
  nodes: [
    { ...heidegger, local: true, record_count: 4, record_ids: [] },
    { ...presence, local: true, record_count: 9, record_ids: [] },
  ],
  linked_records: [
    {
      record_id: "derrida-grammatology-0150",
      preview: "Presence again, read against Heidegger.",
      score: 1.4,
      shared_node_count: 2,
      shared_nodes: [heidegger, presence],
      shared_relation_ids: [],
    },
  ],
} as unknown as RecordSemanticMap;

const neighborhood = {
  node: { ...heidegger, record_ids: [], record_count: 4 },
  nodes: [presence],
  edges: [
    {
      id: "rel:1",
      source: heidegger.id,
      target: presence.id,
      predicate: "questions",
      relation_kind: "semantic",
      authority_status: "human_confirmed",
      record_ids: ["derrida-grammatology-0142"],
    },
    {
      id: "rel:2",
      source: heidegger.id,
      target: presence.id,
      predicate: "co_occurs_with",
      relation_kind: "observational",
      authority_status: "unreviewed",
      record_ids: ["derrida-grammatology-0150"],
    },
  ],
  total_edges: 2,
  records: [
    { record_id: "derrida-grammatology-0142", preview: "Heidegger questions presence." },
    { record_id: "derrida-grammatology-0150", preview: "Presence again." },
  ],
  total_records: 2,
} as unknown as SemanticNodeNeighborhood;

const meta = {
  title: "Corpus Builder/Review/Semantic Map Lists",
  component: RecordSemanticMapLists,
  args: { map, neighborhood: null, recordId: "derrida-grammatology-0142", idPrefix: "story" },
} satisfies Meta<typeof RecordSemanticMapLists>;

export default meta;
type Story = StoryObj<typeof meta>;

export const RecordStep: Story = {};
export const EntityStep: Story = { args: { map: null, neighborhood } };
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
