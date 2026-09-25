import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusTextCleanupSummary from "./CorpusTextCleanupSummary.vue";
const meta = {
  title: "Corpus Builder/Review/Text Cleanup Summary",
  component: CorpusTextCleanupSummary,
  args: {
    summary: {
      enabled: true,
      records_changed: 31,
      changes: 74,
      removed_lines: 42,
      recurring_line_patterns: 5,
      rules: ["page_numbers", "repeated_short_lines", "paragraph_lines", "ocr_artifacts"],
    },
  },
} satisfies Meta<typeof CorpusTextCleanupSummary>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Applied: Story = {};
export const NoChanges: Story = {
  args: {
    summary: {
      enabled: true,
      records_changed: 0,
      changes: 0,
      removed_lines: 0,
      recurring_line_patterns: 0,
    },
  },
};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
