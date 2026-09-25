import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusEditorialMemoryDialog from "./CorpusEditorialMemoryDialog.vue";
const memory = {
  conventions: { discourse_role: { value: "reported_position", confirmed_records: 5 } },
  examples: {
    discourse_role: [
      {
        record_id: "r-17",
        value: "reported_position",
        similarity: 0.72,
        excerpt:
          "Derrida introduces a proposition attributed to Heidegger before turning to his own analysis.",
      },
    ],
  },
  convention_count: 1,
  example_count: 1,
};
const meta = {
  title: "Corpus Builder/Review/Editorial Memory",
  component: CorpusEditorialMemoryDialog,
  args: { open: true, memory },
} satisfies Meta<typeof CorpusEditorialMemoryDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Active: Story = {};
export const Empty: Story = {
  args: { memory: { conventions: {}, examples: {}, convention_count: 0, example_count: 0 } },
};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
