// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { MetadataMemoryEntry } from "../../api/metadataMemory";
import MetadataMemoryTable from "./MetadataMemoryTable.vue";

const base: MetadataMemoryEntry = {
  id: "mex-1",
  memory_type: "evidence_bound",
  kind: "positive",
  field: "position_holder",
  value: "Levinas",
  authority: "human_review",
  record_id: "r1",
  record_revision: 4,
  build_id: "build-1",
  schema_id: "author",
  schema_version: "v1",
  language: "en",
  page_start: 12,
  evidence_bound: true,
  evidence_block_ids: ["b2"],
  evidence_text: "For Levinas, responsibility precedes freedom.",
  context_text: "Context around the evidence.",
  source_current: true,
};

const meta = {
  title: "Metadata memory/Table",
  component: MetadataMemoryTable,
  args: { items: [base] },
} satisfies Meta<typeof MetadataMemoryTable>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const CorrectionAndStale: Story = {
  args: {
    items: [
      {
        ...base,
        id: "mex-2",
        kind: "correction",
        value: "Levinas",
        rejected_value: "Author",
        source_current: false,
      },
    ],
  },
};
export const Loading: Story = { args: { loading: true } };
export const EmptyNoPrecedents: Story = { args: { items: [] } };
export const EmptyFiltered: Story = { args: { items: [], filtered: true } };
