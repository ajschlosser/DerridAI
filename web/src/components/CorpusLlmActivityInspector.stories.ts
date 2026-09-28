import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusLlmActivityInspector from "./CorpusLlmActivityInspector.vue";

const meta = {
  title: "Corpus Builder/Workflow/Model Activity Inspector",
  component: CorpusLlmActivityInspector,
  args: {
    // Closed by default: Storybook never performs an API read or opens a realtime subscription.
    buildId: "storybook-build",
  },
} satisfies Meta<typeof CorpusLlmActivityInspector>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ClosedOptIn: Story = {};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
