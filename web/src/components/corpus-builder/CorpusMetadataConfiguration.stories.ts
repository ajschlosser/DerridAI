import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusMetadataConfiguration from "./CorpusMetadataConfiguration.vue";

const schemaChoices = [
  {
    id: "default",
    name: "DerridAI default",
    description: "Default scholarly metadata",
    builtin: true,
    field_count: 8,
    groups: ["discourse"],
    hash: "default-hash",
  },
  {
    id: "custom",
    name: "Attribution study",
    description: "Speaker, target, stance, and discourse-role metadata",
    builtin: false,
    field_count: 14,
    groups: ["discourse", "attribution"],
    hash: "custom-hash",
  },
];

const meta = {
  title: "Corpus Builder/Setup/Metadata Configuration",
  component: CorpusMetadataConfiguration,
  args: {
    schemaId: "default",
    runGuidance: {},
    schemaChoices,
    chosenSchema: schemaChoices[0],
    runGuidanceFields: [
      { name: "speaker", label: "Speaker", group: "Discourse" },
      { name: "position_holder", label: "Position holder", group: "Attribution" },
    ],
    disabled: false,
  },
} satisfies Meta<typeof CorpusMetadataConfiguration>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const CustomSchema: Story = {
  args: {
    schemaId: "custom",
    chosenSchema: schemaChoices[1],
    runGuidance: {
      speaker: {
        instructions: "Distinguish Derrida's voice from quoted or attributed positions.",
        look_for: ["Derrida", "Levinas", "Heidegger"],
      },
    },
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
