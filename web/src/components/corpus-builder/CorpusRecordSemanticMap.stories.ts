/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { RecordSemanticMap, SemanticNodeNeighborhood } from "../../api/corpus";
import CorpusRecordSemanticMap from "./CorpusRecordSemanticMap.vue";

const text =
  "Heidegger questions the metaphysics of presence, and Author reads the trace against Levinas.";
const span = (surface: string) => ({
  start: text.indexOf(surface),
  end: text.indexOf(surface) + surface.length,
});
const node = (id: string, label: string, type: string, local = true, records = 2) => ({
  id,
  label,
  type,
  local,
  record_count: records,
  record_ids: [],
});

const recordMap: RecordSemanticMap = {
  version: 1,
  kind: "record_semantic_map",
  record_id: "author-grammatology-0142",
  record_revision: 3,
  record_text_sha256: "story",
  layers: {
    document_intelligence: { status: "ok", provider: "booknlp", profile: "scholarly" },
    terms: { status: "ok" },
  },
  mentions: [
    {
      ...span("Heidegger"),
      text: "Heidegger",
      layer: "entity",
      tag: "PERSON",
      node_id: "person:heidegger",
    },
    {
      ...span("metaphysics"),
      text: "metaphysics",
      layer: "pos",
      tag: "NOUN",
      node_id: "term:metaphysics",
    },
    {
      ...span("presence"),
      text: "presence",
      layer: "pos",
      tag: "NOUN",
      node_id: "concept:presence",
    },
    { ...span("Author"), text: "Author", layer: "ner", tag: "PERSON", node_id: "person:author" },
    { ...span("trace"), text: "trace", layer: "pos", tag: "NOUN", node_id: "concept:trace" },
    {
      ...span("Levinas"),
      text: "Levinas",
      layer: "entity",
      tag: "PERSON",
      node_id: "person:levinas",
    },
  ],
  nodes: [
    node("person:heidegger", "Martin Heidegger", "person", true, 14),
    node("concept:presence", "presence", "concept", true, 22),
    node("person:author", "Jane Author", "person", true, 40),
    node("concept:trace", "trace", "concept", true, 9),
    node("person:levinas", "Emmanuel Levinas", "person", true, 6),
    node("term:metaphysics", "metaphysics", "term", true, 11),
    node("work:being-and-time", "Being and Time", "work", false, 4),
    node("concept:logocentrism", "logocentrism", "concept", false, 7),
  ],
  edges: [
    {
      id: "rel:questions",
      source: "person:heidegger",
      target: "concept:presence",
      predicate: "questions",
      relation_kind: "semantic",
      authority_status: "human_confirmed",
      record_ids: ["author-grammatology-0142"],
      in_record: true,
    },
    {
      id: "rel:co",
      source: "concept:trace",
      target: "person:author",
      predicate: "co_occurs",
      relation_kind: "observational",
      record_ids: ["author-grammatology-0142"],
      in_record: true,
    },
    {
      id: "rel:work",
      source: "person:heidegger",
      target: "work:being-and-time",
      predicate: "quoted_work",
      relation_kind: "semantic",
      record_ids: ["author-grammatology-0098"],
      in_record: false,
    },
    {
      id: "rel:logos",
      source: "concept:presence",
      target: "concept:logocentrism",
      predicate: "co_occurs",
      relation_kind: "observational",
      record_ids: ["author-grammatology-0151"],
      in_record: false,
    },
  ],
  linked_records: [
    {
      record_id: "author-grammatology-0151",
      preview: "The privilege of presence as consciousness is the matrix of logocentrism…",
      score: 3.214,
      shared_node_count: 3,
      shared_nodes: [
        { id: "concept:presence", label: "presence", type: "concept" },
        { id: "concept:trace", label: "trace", type: "concept" },
        { id: "term:metaphysics", label: "metaphysics", type: "term" },
      ],
      shared_relation_ids: [],
    },
    {
      record_id: "author-grammatology-0098",
      preview: "In Being and Time the question of the meaning of Being is posed anew…",
      score: 1.91,
      shared_node_count: 1,
      shared_nodes: [{ id: "person:heidegger", label: "Martin Heidegger", type: "person" }],
      shared_relation_ids: ["rel:questions"],
    },
  ],
  summary: {
    local_nodes: 6,
    shown_local_nodes: 6,
    neighbor_nodes: 2,
    in_record_edges: 2,
    outward_edges: 2,
    linked_records: 2,
  },
  epistemic_note:
    "A shared node, term, or relation shows where Records meet in the derived graph. It is a navigation aid, not evidence that the Records make the same claim.",
};

const neighborhood: SemanticNodeNeighborhood = {
  version: 1,
  kind: "semantic_node_neighborhood",
  node: {
    ...node("person:heidegger", "Martin Heidegger", "person", true, 14),
    aliases: ["Heidegger"],
  },
  nodes: [
    node("concept:presence", "presence", "concept"),
    node("work:being-and-time", "Being and Time", "work"),
  ],
  edges: recordMap.edges.filter((edge) => edge.source === "person:heidegger"),
  total_edges: 2,
  records: [
    { record_id: "author-grammatology-0142", preview: text },
    { record_id: "author-grammatology-0098", preview: "In Being and Time the question…" },
  ],
  total_records: 14,
};

function stubFetch(map: RecordSemanticMap) {
  const original = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input instanceof Request ? input.url : input);
    const body = url.includes("/semantic-map")
      ? map
      : url.includes("/semantic-content-graph/nodes/")
        ? neighborhood
        : null;
    if (!body) return original(input, init);
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
}

const meta = {
  title: "Corpus Builder/Review/Record Semantic Map",
  component: CorpusRecordSemanticMap,
  args: {
    buildId: "build-story",
    record: { record_id: "author-grammatology-0142", text, record_revision: 3 },
    disabled: false,
  },
  decorators: [
    (story, context) => {
      stubFetch((context.parameters.recordMap as RecordSemanticMap) || recordMap);
      return story();
    },
  ],
} satisfies Meta<typeof CorpusRecordSemanticMap>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Scholarly: Story = {};

export const StaleLayers: Story = {
  parameters: {
    recordMap: {
      ...recordMap,
      layers: {
        document_intelligence: { status: "stale", provider: "spacy" },
        terms: { status: "missing" },
      },
      mentions: [],
    },
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
