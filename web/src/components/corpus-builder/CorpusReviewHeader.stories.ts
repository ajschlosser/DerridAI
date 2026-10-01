import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusReviewHeader from "./CorpusReviewHeader.vue";

// Everything the header does not declare falls through to the toolbar below it.
const toolbar = {
  total: 177,
  metadata: 2,
  topology: 1,
  sourceProblems: 1,
  rejected: 3,
  bulkActionItems: [{ id: "reject-selected", label: "Reject selected" }],
  bulkActionFeedback: "",
  bulkMetadataOpen: false,
  schema: null,
  knownValues: {},
  regionTypes: [],
  discourseRoles: [],
  selectedCount: 0,
  bulkTotalCount: 177,
  bulkDisabled: false,
  pageNumber: 1,
  pageCount: 4,
  hasPreviousPage: false,
  hasNextPage: true,
  disabled: false,
};

const meta = {
  title: "Corpus Builder/Review/Header",
  component: CorpusReviewHeader,
  args: {
    queue: "all",
    query: "",
    accepted: 142,
    ready: 17,
    issues: 4,
    remaining: 31,
    reviewTotal: 60,
    workspaceMode: "record",
    hasSelectedRecord: true,
  },
  render: (args) => ({
    components: { CorpusReviewHeader },
    setup: () => ({ args, toolbar }),
    template: `<CorpusReviewHeader v-bind="{ ...toolbar, ...args }" />`,
  }),
} satisfies Meta<typeof CorpusReviewHeader>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const IssuesQueue: Story = { args: { queue: "metadata", query: "Levinas" } };
export const NoSelectedRecord: Story = { args: { hasSelectedRecord: false, focusDisabled: true } };
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
