import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { CorpusRecord } from "../../api/corpus";
import CorpusReviewToolbar from "./CorpusReviewToolbar.vue";

const records: CorpusRecord[] = [
  {
    record_id: "record-1",
    text: "A representative record under review.",
    text_length: 37,
    source_block_ids: [],
    source_spans: [],
  },
];

const meta = {
  title: "Corpus Builder/Review/Toolbar",
  component: CorpusReviewToolbar,
  args: {
    queue: "all",
    query: "",
    total: 48,
    ready: 17,
    issues: 9,
    metadata: 5,
    topology: 3,
    sourceProblems: 1,
    accepted: 19,
    rejected: 3,
    workspaceMode: "record",
    hasSelectedRecord: true,
    bulkActionItems: [
      { id: "bulk-edit", label: "Bulk edit metadata" },
      { id: "reject-selected", label: "Reject selected" },
    ],
    bulkActionFeedback: "",
    bulkMetadataOpen: false,
    schema: null,
    records,
    knownValues: {},
    regionTypes: ["argument", "quotation"],
    discourseRoles: ["claim", "attribution"],
    selectedCount: 2,
    bulkTotalCount: 48,
    bulkDisabled: false,
    pageNumber: 1,
    pageCount: 4,
    hasPreviousPage: false,
    hasNextPage: true,
    disabled: false,
  },
} satisfies Meta<typeof CorpusReviewToolbar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const NoSelectedRecord: Story = {
  args: {
    hasSelectedRecord: false,
  },
};

export const IssuesQueue: Story = {
  args: {
    queue: "metadata",
    query: "Levinas",
    workspaceMode: "metadata",
  },
};

export const BulkFeedback: Story = {
  args: {
    bulkActionFeedback: "Updated metadata on 2 selected records.",
  },
};

export const Busy: Story = {
  args: {
    disabled: true,
    bulkDisabled: true,
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
