import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusTextCleanupDialog from "./CorpusTextCleanupDialog.vue";
const meta = {
  title: "Corpus Builder/Review/Text Cleanup",
  component: CorpusTextCleanupDialog,
  args: {
    text: "CHAPTER ONE\n12\nThis is philoso-\nphical text.\n\n\nCHAPTER ONE\n13\nMore text.",
    recurringLines: ["CHAPTER ONE"],
  },
} satisfies Meta<typeof CorpusTextCleanupDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
