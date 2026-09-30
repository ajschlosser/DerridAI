import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusReviewInspector from "./CorpusReviewInspector.vue";

const meta = {
  title: "Corpus Builder/Review/Inspector",
  component: CorpusReviewInspector,
  args: { mode: "record", hasRecord: true, blockerCount: 2, tab: "metadata" },
  render: (args) => ({
    components: { CorpusReviewInspector },
    setup: () => ({ args }),
    template: `<div style="height: 24rem; display: grid"><CorpusReviewInspector v-bind="args"><p style="padding: 1rem">Active panel</p></CorpusReviewInspector></div>`,
  }),
} satisfies Meta<typeof CorpusReviewInspector>;
export default meta;
type Story = StoryObj<typeof meta>;

export const SplitView: Story = {};
export const EvidenceTab: Story = { args: { tab: "evidence", blockerCount: 0 } };
export const MetadataWorkspace: Story = { args: { mode: "metadata" } };
export const SourceWorkspace: Story = { args: { mode: "source" } };
