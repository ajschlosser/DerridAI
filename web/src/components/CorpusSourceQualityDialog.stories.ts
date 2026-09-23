import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusSourceQualityDialog from "./CorpusSourceQualityDialog.vue";

const meta = {
  title: "Corpus Builder/Review/Source Quality Dialog",
  component: CorpusSourceQualityDialog,
  args: {
    open: true,
    extractionNoise: {
      page_count: 12,
      unusable_page_count: 3,
      unusable_page_ratio: 0.25,
      median_noise: 52,
      threshold: 45,
      exceeds_threshold: true,
    },
    issues: [
      {
        code: "illegible_text",
        severity: "blocking",
        pages: [24],
        message: "Extracted text does not look like words in a writing system.",
      },
    ],
  },
} satisfies Meta<typeof CorpusSourceQualityDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const IngestWarning: Story = {};
export const RecordWarning: Story = {
  args: {
    extractionNoise: null,
    issues: [
      {
        code: "low_raster_quality",
        severity: "blocking",
        pages: [8],
        message: "Embedded page image resolution is too low to trust as a scholarly scan.",
      },
    ],
  },
};
