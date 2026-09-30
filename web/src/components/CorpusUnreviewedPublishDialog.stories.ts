import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusUnreviewedPublishDialog from "./CorpusUnreviewedPublishDialog.vue";

const meta = {
  title: "Corpus Builder/Publication/Unreviewed publish decision",
  component: CorpusUnreviewedPublishDialog,
  args: {
    open: true,
    busy: false,
    pendingRecords: 18,
    unresolvedFields: 31,
  },
} satisfies Meta<typeof CorpusUnreviewedPublishDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Busy: Story = {
  args: { busy: true },
};

export const LargeReviewScope: Story = {
  args: {
    pendingRecords: 248,
    unresolvedFields: 913,
  },
};
