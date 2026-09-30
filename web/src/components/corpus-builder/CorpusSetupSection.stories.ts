import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusSetupSection from "./CorpusSetupSection.vue";

const meta = {
  title: "Corpus Builder/Setup/Section",
  component: CorpusSetupSection,
  args: {
    id: "source",
    title: "Source",
    description: "Choose the document this build will read.",
    state: "complete",
    summary: "Of Grammatology.pdf · PDF · 437 pages",
    expanded: false,
  },
  render: (args) => ({
    components: { CorpusSetupSection },
    setup: () => ({ args }),
    template: `<CorpusSetupSection v-bind="args"><p>Section controls appear here.</p></CorpusSetupSection>`,
  }),
} satisfies Meta<typeof CorpusSetupSection>;
export default meta;
type Story = StoryObj<typeof meta>;

export const CompleteCollapsed: Story = {};
export const Expanded: Story = { args: { expanded: true } };
export const Incomplete: Story = {
  args: { state: "incomplete", summary: "No source selected", expanded: true },
};
export const Warning: Story = {
  args: {
    id: "metadata",
    title: "Metadata",
    state: "warning",
    summary: "Scholarly default · 2 document fields need attention",
  },
};
export const Optional: Story = {
  args: { id: "advanced", title: "Advanced", state: "optional", summary: "Run policy defaults" },
};
export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    title: "Interprétation de la structure documentaire",
    summary:
      "Jacques Derrida — Cosmopolites de tous les pays, encore un effort ! — édition critique.pdf · PDF · 437 pages",
  },
};
