import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import ResearchObjectDiagram from "./ResearchObjectDiagram.vue";

const nodes = [
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
    label: "Source passage",
    summary: "Printed page 158",
    materialization: "embedded",
  },
  {
    id: "Record:r1",
    object_type: "Record",
    object_id: "r1",
    label: "Record r1",
    summary: "Of Grammatology · p. 158",
    materialization: "materialized",
  },
  {
    id: "RecordRevision:r1@3",
    object_type: "RecordRevision",
    object_id: "r1@3",
    label: "Revision 3",
    summary: "Current evidence-bearing state",
    materialization: "materialized",
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
  {
    id: "ResearchRun:run9",
    object_type: "ResearchRun",
    object_id: "run9",
    label: "Research run run9",
    summary: "Retained research operation",
    materialization: "reference",
  },
];

const edges = [
  {
    id: "d-s",
    source: "SourceDocument:d1",
    target: "SourceSpan:s1",
    relation: "contains span",
    inverse_relation: "belongs to document",
    normative: true,
  },
  {
    id: "d-r",
    source: "SourceDocument:d1",
    target: "Record:r1",
    relation: "contains record",
    inverse_relation: "belongs to document",
    normative: true,
  },
  {
    id: "r-s",
    source: "Record:r1",
    target: "SourceSpan:s1",
    relation: "derives from",
    inverse_relation: "contributes to",
    normative: true,
  },
  {
    id: "r-rev",
    source: "Record:r1",
    target: "RecordRevision:r1@3",
    relation: "has revision",
    inverse_relation: "revision of",
    normative: true,
  },
  {
    id: "r-a",
    source: "Record:r1",
    target: "FieldAssertion:a1",
    relation: "has assertion",
    inverse_relation: "assertion in context of",
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
  {
    id: "run-c",
    source: "ResearchRun:run9",
    target: "GeneratedClaim:c1",
    relation: "contains generated claim",
    inverse_relation: "generated in research run",
    normative: false,
  },
];

const meta = {
  title: "Record Workspace/Research Object Diagram",
  component: ResearchObjectDiagram,
  render: (args) => ({
    components: { ResearchObjectDiagram },
    setup() {
      const focusId = ref(args.focusId || "Record:r1");
      return { args, focusId };
    },
    template:
      '<ResearchObjectDiagram v-bind="args" :focus-id="focusId" @focus="focusId = $event" />',
  }),
  args: {
    nodes,
    edges,
    focusId: "Record:r1",
    ariaLabel: "Example record relationship diagram",
  },
} satisfies Meta<typeof ResearchObjectDiagram>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SourceToClaimWithMetadataBranch: Story = {};
