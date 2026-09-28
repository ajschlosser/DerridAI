import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusDocumentIntelligenceStatus from "./CorpusDocumentIntelligenceStatus.vue";

const meta = {
  title: "Corpus Builder/Workflow/Document Intelligence Status",
  component: CorpusDocumentIntelligenceStatus,
  args: {
    requestedProvider: "auto",
    run: {
      status: "ok",
      profile: "scholarly",
      selected_provider: "auto",
      provider: "booknlp",
      provider_version: "1.0",
      model: "big",
      capabilities: ["entities", "coreference", "quotations", "speaker_attribution"],
      entity_mentions: 184,
      quotations: 37,
      events: 0,
      warnings: [],
    },
  },
} satisfies Meta<typeof CorpusDocumentIntelligenceStatus>;

export default meta;
type Story = StoryObj<typeof meta>;

export const BookNlpCompleted: Story = {};

export const AutomaticFallback: Story = {
  args: {
    run: {
      status: "ok",
      profile: "scholarly",
      selected_provider: "auto",
      provider: "spacy",
      provider_version: "3.8",
      model: "en_core_web_sm",
      capabilities: ["entities"],
      entity_mentions: 121,
      quotations: 0,
      events: 0,
      warnings: ["BookNLP unavailable: provider connection failed"],
    },
  },
};

export const Unavailable: Story = {
  args: {
    requestedProvider: "booknlp",
    run: {
      status: "unavailable",
      profile: "scholarly",
      selected_provider: "booknlp",
      provider: "booknlp",
      reason: "provider_unavailable",
      entity_mentions: 0,
      quotations: 0,
      events: 0,
      warnings: ["BookNLP unavailable"],
    },
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: AutomaticFallback.args,
};
