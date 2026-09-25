import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusReviewSessionBar from "./CorpusReviewSessionBar.vue";

const meta = {
  title: "Corpus Builder/Review/Session Header",
  component: CorpusReviewSessionBar,
  args: {
    sourceFilename: "On Cosmopolitanism and Forgiveness.pdf",
    model: "Gemma 4 26B",
    buildId: "build-20260918",
    accepted: 18,
    reviewable: 11,
    remaining: 42,
    issues: 7,
  },
} satisfies Meta<typeof CorpusReviewSessionBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const FocusDisabled: Story = {
  args: { focusDisabled: true },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    sourceFilename:
      "Cosmopolites de tous les pays, encore un effort ! — édition critique commentée et révisée.pdf",
    model: "Modèle local de synthèse et d’attribution avec contexte documentaire étendu",
  },
};

export const Narrow: Story = {
  args: {
    sourceFilename:
      "Entretien enregistré — transcription révisée avec identification détaillée des locuteurs.flac",
    model: "Local attribution model with extended provenance context",
  },
  decorators: [
    (story) => ({
      components: { story },
      template: '<div style="max-width: 360px"><story /></div>',
    }),
  ],
};
