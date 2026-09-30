import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusReviewInspector from "./CorpusReviewInspector.vue";

const meta = {
  title: "Corpus Builder/Review/Inspector",
  component: CorpusReviewInspector,
  args: { mode: "record", hasRecord: true, blockerCount: 2, tab: "metadata" },
  render: (args) => ({
    components: { CorpusReviewInspector },
    setup: () => ({ args }),
    template: `<div style="height: 24rem; display: grid"><CorpusReviewInspector v-bind="args">
      <section v-for="id in ['metadata', 'evidence', 'source', 'semantic']" :id="'review-panel-' + id" :key="id" role="tabpanel" :aria-labelledby="'review-tab-' + id" :hidden="args.tab !== id" tabindex="0" style="padding: 1rem">Active panel: {{ id }}</section>
    </CorpusReviewInspector></div>`,
  }),
} satisfies Meta<typeof CorpusReviewInspector>;
export default meta;
type Story = StoryObj<typeof meta>;

export const SplitView: Story = {};
export const EvidenceTab: Story = { args: { tab: "evidence", blockerCount: 0 } };
export const MetadataWorkspace: Story = { args: { mode: "metadata" } };
export const SourceWorkspace: Story = { args: { mode: "source" } };
