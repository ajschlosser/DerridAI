import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordTraceabilityExplorer from "./RecordTraceabilityExplorer.vue";

const graph = {
  specification_version: "1.0",
  root_id: "Record:r1",
  nodes: [
    { id: "Record:r1", object_type: "Record", object_id: "r1", label: "Record r1", summary: "Of Grammatology · pp. 12–13", materialization: "materialized" },
    { id: "SourceDocument:d1", object_type: "SourceDocument", object_id: "d1", label: "Of Grammatology", summary: "Jacques Derrida", materialization: "materialized" },
    { id: "SourceSpan:s1", object_type: "SourceSpan", object_id: "s1", label: "Source span s1", summary: "Page 12", materialization: "embedded" },
    { id: "FieldAssertion:a1", object_type: "FieldAssertion", object_id: "a1", label: "position_holder", summary: "Levinas", materialization: "materialized", status: "human_confirmed" },
  ],
  edges: [
    { id: "d-r", source: "SourceDocument:d1", target: "Record:r1", relation: "contains record", inverse_relation: "belongs to document", normative: true, source_cardinality: "0..*", target_cardinality: "1", profile: "Core" },
    { id: "r-s", source: "Record:r1", target: "SourceSpan:s1", relation: "derives from", inverse_relation: "contributes to", normative: true, source_cardinality: "1..*", target_cardinality: "0..*", profile: "Core" },
    { id: "r-a", source: "Record:r1", target: "FieldAssertion:a1", relation: "has assertion", inverse_relation: "assertion in context of", normative: true, source_cardinality: "0..*", target_cardinality: "1", profile: "Core" },
  ],
};

const model = {
  specification_version: "1.0",
  nodes: [
    { type: "SourceDocument", label: "Source document", profile: "Core", persistence: "durable", normative: true },
    { type: "Record", label: "Record", profile: "Core", persistence: "durable", normative: true },
    { type: "SourceSpan", label: "Source span", profile: "Core", persistence: "durable_locator", normative: true },
  ],
  edges: [
    { id: "source_document_records", source_type: "SourceDocument", target_type: "Record", relation: "contains record", inverse_relation: "belongs to document", source_cardinality: "0..*", target_cardinality: "1", profile: "Core", normative: true },
    { id: "record_spans", source_type: "Record", target_type: "SourceSpan", relation: "derives from", inverse_relation: "contributes to", source_cardinality: "1..*", target_cardinality: "0..*", profile: "Core", normative: true },
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
