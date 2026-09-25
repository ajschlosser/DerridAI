import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusRunGuidance from "./CorpusRunGuidance.vue";

const fields = [
  { name: "persons", label: "People", group: "indexing" },
  { name: "works_referenced", label: "Works cited in the argument", group: "indexing" },
  { name: "concepts", label: "Concepts", group: "indexing" },
];

const meta = {
  title: "Corpus Builder/Setup/Run Guidance",
  component: CorpusRunGuidance,
  args: {
    fields,
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

export const Empty: Story = {
  args: { modelValue: {} },
};

export const RequiredFallback: Story = {
  args: {
    modelValue: {
      persons: {
        instructions:
          "Identify the position holder only when the passage supports the attribution.",
        look_for: ["Emmanuel Levinas"],
        required: true,
        default_placeholder: "[not established in source]",
      },
    },
  },
};

export const Disabled: Story = {
  args: {
    disabled: true,
  },
};

export const FrenchLongText: Story = {
  args: {
    fields: [
      {
        name: "position_holder",
        label: "Détenteur de la position philosophique attribuée dans le passage",
        group: "provenance et attribution",
      },
      {
        name: "works_referenced",
        label: "Œuvres explicitement discutées dans l’argument",
        group: "indexation",
      },
    ],
    modelValue: {
      position_holder: {
        instructions:
          "Distinguer la personne qui parle de la personne dont la position est exposée, citée, contestée ou provisoirement acceptée.",
        look_for: ["Emmanuel Levinas", "Martin Heidegger", "Immanuel Kant"],
        required: true,
        default_placeholder: "[non établi dans la source]",
      },
    },
  },
  decorators: [
    (story) => ({
      components: { story },
      template: '<div style="max-width: 520px"><story /></div>',
    }),
  ],
};
