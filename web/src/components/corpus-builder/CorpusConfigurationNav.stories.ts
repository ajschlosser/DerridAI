import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusConfigurationNav from "./CorpusConfigurationNav.vue";

const meta = {
  title: "Corpus Builder/Setup/Configuration Navigation",
  component: CorpusConfigurationNav,
  args: {
    modelValue: "source",
    hasSource: true,
    structureAvailable: true,
  },
} satisfies Meta<typeof CorpusConfigurationNav>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Source: Story = {};

export const Enrichment: Story = {
  args: { modelValue: "enrichment" },
};

export const NoSource: Story = {
  args: {
    modelValue: "source",
    hasSource: false,
    structureAvailable: false,
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: { modelValue: "metadata" },
};
