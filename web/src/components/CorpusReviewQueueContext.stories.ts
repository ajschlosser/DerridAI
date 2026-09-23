// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3";
import CorpusReviewQueueContext from "./CorpusReviewQueueContext.vue";

const meta = {
  title: "Corpus/Review Queue Context",
  component: CorpusReviewQueueContext,
  args: {
    currentRecordId: "record-002",
    justProcessedRecordId: "record-001",
    nextRecordId: "record-003",
  },
  render: (args) => ({
    components: { CorpusReviewQueueContext },
    setup: () => ({ args }),
    template:
      '<CorpusReviewQueueContext v-bind="args" @navigate-record="(recordId) => window.alert(recordId)" />',
  }),
} satisfies Meta<typeof CorpusReviewQueueContext>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const AtQueueEnd: Story = {
  args: {
    currentRecordId: "record-002",
    justProcessedRecordId: "record-001",
    nextRecordId: undefined,
  },
};
