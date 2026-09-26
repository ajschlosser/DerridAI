import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordTraceabilityExplorer from "./RecordTraceabilityExplorer.vue";

const graph = {
  specification_version: "1.0",
  root_id: "Record:r1",
  nodes: [
    {
      id: "Record:r1",
      object_type: "Record",
      object_id: "r1",
      label: "Record r1",
      summary: "Of Grammatology · pp. 12–13",
      materialization: "materialized",
    },
    {
      id: "SourceDocument:d1",
      object_type: "SourceDocument",
      object_id: "d1",
      label: "Of Grammatology",
      summary: "Jacques Derrida",
      materialization: "materialized",
    },
    {
      id: "SourceSpan:s1",
      object_type: "SourceSpan",
      object_id: "s1",
      label: "Source span s1",
      summary: "Page 12",
      materialization: "embedded",
    },
    {
      id: "FieldAssertion:a1",
      object_type: "FieldAssertion",
      object_id: "a1",
      label: "position_holder",
      summary: "Levinas",
      materialization: "materialized",
      status: "human_confirmed",
    },
  ],
  edges: [
    {
      id: "d-r",
      source: "SourceDocument:d1",
      target: "Record:r1",
      relation: "contains record",
      inverse_relation: "belongs to document",
      normative: true,
      source_cardinality: "0..*",
      target_cardinality: "1",
      profile: "Core",
    },
    {
      id: "r-s",
      source: "Record:r1",
      target: "SourceSpan:s1",
      relation: "derives from",
      inverse_relation: "contributes to",
      normative: true,
      source_cardinality: "1..*",
      target_cardinality: "0..*",
      profile: "Core",
    },
    {
      id: "r-a",
      source: "Record:r1",
      target: "FieldAssertion:a1",
      relation: "has assertion",
      inverse_relation: "assertion in context of",
      normative: true,
      source_cardinality: "0..*",
      target_cardinality: "1",
      profile: "Core",
    },
  ],
};

const model = {
  specification_version: "1.0",
  nodes: [
    {
      type: "SourceDocument",
      label: "Source document",
      profile: "Core",
      persistence: "durable",
      normative: true,
    },
    { type: "Record", label: "Record", profile: "Core", persistence: "durable", normative: true },
    {
      type: "SourceSpan",
      label: "Source span",
      profile: "Core",
      persistence: "durable_locator",
      normative: true,
    },
  ],
  edges: [
    {
      id: "source_document_records",
      source_type: "SourceDocument",
      target_type: "Record",
      relation: "contains record",
      inverse_relation: "belongs to document",
      source_cardinality: "0..*",
      target_cardinality: "1",
      profile: "Core",
      normative: true,
    },
    {
      id: "record_spans",
      source_type: "Record",
      target_type: "SourceSpan",
      relation: "derives from",
      inverse_relation: "contributes to",
      source_cardinality: "1..*",
      target_cardinality: "0..*",
      profile: "Core",
      normative: true,
    },
  ],
};

const meta = {
  title: "Record Workspace/Traceability Explorer",
  component: RecordTraceabilityExplorer,
  args: { graph, model },
} satisfies Meta<typeof RecordTraceabilityExplorer>;
export default meta;
type Story = StoryObj<typeof meta>;
export const BranchingRecord: Story = {};

export const WithResearchUse: Story = {
  args: {
    graph: {
      ...graph,
      nodes: [
        ...graph.nodes,
        {
          id: "RecordRevision:r1@3",
          object_type: "RecordRevision",
          object_id: "r1@3",
          label: "Revision 3",
          summary: "Evidence-bearing state",
          materialization: "materialized",
        },
        {
          id: "EvidenceRef:e1",
          object_type: "EvidenceRef",
          object_id: "e1",
          label: "Evidence reference e1",
          summary: "Record r1 · revision 3",
          materialization: "embedded",
        },
        {
          id: "SupportBinding:b1",
          object_type: "SupportBinding",
          object_id: "b1",
          label: "Support binding b1",
          summary: "supports",
          materialization: "materialized",
          status: "validated",
        },
        {
          id: "GeneratedClaim:c1",
          object_type: "GeneratedClaim",
          object_id: "c1",
          label: "Generated claim",
          summary: "Writing is not simply secondary to speech.",
          materialization: "materialized",
          status: "validated",
        },
      ],
      edges: [
        ...graph.edges,
        {
          id: "r-rev",
          source: "Record:r1",
          target: "RecordRevision:r1@3",
          relation: "has revision",
          inverse_relation: "revision of",
          normative: true,
        },
        {
          id: "e-rev",
          source: "EvidenceRef:e1",
          target: "RecordRevision:r1@3",
          relation: "locates revision",
          inverse_relation: "referenced by evidence",
          normative: true,
        },
        {
          id: "b-e",
          source: "SupportBinding:b1",
          target: "EvidenceRef:e1",
          relation: "binds evidence",
          inverse_relation: "bound by",
          normative: true,
        },
        {
          id: "c-b",
          source: "GeneratedClaim:c1",
          target: "SupportBinding:b1",
          relation: "has support binding",
          inverse_relation: "binds claim",
          normative: true,
        },
      ],
    },
  },
};
