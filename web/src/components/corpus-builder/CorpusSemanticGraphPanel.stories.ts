/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusSemanticGraphPanel from "./CorpusSemanticGraphPanel.vue";

const meta = {
  title: "Corpus Builder/Review/Semantic Content Graph",
  component: CorpusSemanticGraphPanel,
  args: {
    buildId: "build-document-intelligence",
    summary: {
      nodes: 42,
      edges: 67,
      characters: 0,
      persons: 14,
      concepts: 19,
      works: 9,
      semantic_edges: 21,
      observational_edges: 46,
    },
    disabled: false,
  },
} satisfies Meta<typeof CorpusSemanticGraphPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ScholarlySummary: Story = {};

export const FictionSummary: Story = {
  args: {
    summary: {
      nodes: 31,
      edges: 54,
      characters: 27,
      persons: 0,
      concepts: 2,
      works: 2,
      semantic_edges: 8,
      observational_edges: 46,
    },
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
