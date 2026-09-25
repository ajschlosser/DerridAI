import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusRevisionHistory from "./CorpusRevisionHistory.vue";
const meta = {
  title: "Corpus Builder/Review/Revision History",
  component: CorpusRevisionHistory,
  args: {
    record: {
      record_id: "r-12",
      text: "Reviewed text",
      text_length: 13,
      source_block_ids: ["b1"],
      source_spans: [{ block_id: "b1", page: 4 }],
      text_revision_history: [
        {
          at: "2026-09-18T10:00:00Z",
          source: "automatic_cleanup",
          previous_length: 92,
          text_length: 83,
          diff: "...",
        },
        {
          at: "2026-09-18T10:04:00Z",
          source: "human",
          previous_length: 83,
          text_length: 86,
          diff: "...",
        },
      ],
      metadata_decisions: [
        { field: "discourse_role", value: "analysis", at: "2026-09-18T10:05:00Z", source: "human" },
      ],
    },
  },
} satisfies Meta<typeof CorpusRevisionHistory>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
