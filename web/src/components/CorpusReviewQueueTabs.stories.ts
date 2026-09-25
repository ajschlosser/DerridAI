import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusReviewQueueTabs from "./CorpusReviewQueueTabs.vue";

const meta = {
  title: "Corpus Builder/Review/Queue Tabs",
  component: CorpusReviewQueueTabs,
  args: {
    modelValue: "ready",
    total: 76,
    ready: 9,
    issues: 6,
    metadata: 3,
    topology: 1,
    sourceProblems: 2,
    accepted: 61,
    rejected: 0,
  },
} satisfies Meta<typeof CorpusReviewQueueTabs>;
export default meta;
type Story = StoryObj<typeof meta>;

export const ExceptionsRemain: Story = {};
export const MetadataQueue: Story = {
  args: {
    modelValue: "metadata",
    ready: 7,
    issues: 4,
    metadata: 4,
    topology: 0,
    sourceProblems: 0,
    accepted: 65,
    rejected: 0,
  },
};
export const SourceProblems: Story = {
  args: {
    modelValue: "source",
    ready: 6,
    issues: 5,
    metadata: 2,
    topology: 1,
    sourceProblems: 2,
    accepted: 65,
    rejected: 0,
  },
};
export const AllReviewed: Story = {
  args: {
    modelValue: "accepted",
    ready: 0,
    issues: 0,
    metadata: 0,
    topology: 0,
    sourceProblems: 0,
    accepted: 76,
    rejected: 0,
  },
};
export const LockedDuringEnrichment: Story = { args: { disabled: true } };
