import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusReviewAdvancedMetadata from "./CorpusReviewAdvancedMetadata.vue";

const meta = {
  title: "Corpus Builder/Review/Advanced Metadata",
  component: CorpusReviewAdvancedMetadata,
  args: {
    busy: false,
    hasManifest: true,
    profiles: [],
    providerId: "",
    modelOverride: "",
    familyOptions: [
      { key: "discourse", label: "Discourse" },
      { key: "quotation", label: "Quotation" },
    ],
    draft: '{\n  "region_type": "argument"\n}',
    family: "all",
  },
  render: (args) => ({
    components: { CorpusReviewAdvancedMetadata },
    setup: () => ({ args }),
    template: `<div style="max-width: 32rem"><CorpusReviewAdvancedMetadata v-bind="args" open /></div>`,
  }),
} satisfies Meta<typeof CorpusReviewAdvancedMetadata>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Busy: Story = { args: { busy: true } };
