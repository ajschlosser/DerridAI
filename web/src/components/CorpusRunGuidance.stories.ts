import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusRunGuidance from "./CorpusRunGuidance.vue";

const meta = {
  title: "Corpus Builder/Setup/Run Guidance",
  component: CorpusRunGuidance,
  args: {
    fields: [
      { name: "persons", label: "People", group: "indexing" },
      { name: "works_referenced", label: "Works cited in the argument", group: "indexing" },
      { name: "concepts", label: "Concepts", group: "indexing" },
    ],
    modelValue: {
      persons: {
        instructions:
          "Include philosophers whose positions are discussed, not incidental names in references.",
        look_for: ["Emmanuel Levinas", "Levinas"],
      },
      works_referenced: {
        instructions: "Include works treated in the body text.",
        look_for: ["Totality and Infinity"],
      },
    },
  },
} satisfies Meta<typeof CorpusRunGuidance>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Seeded: Story = {};
export const Empty: Story = { args: { modelValue: {} } };
