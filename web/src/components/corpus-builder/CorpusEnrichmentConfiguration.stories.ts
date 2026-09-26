import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusEnrichmentConfiguration from "./CorpusEnrichmentConfiguration.vue";

const profiles = [
  {
    id: "local",
    name: "Local Ollama",
    type: "ollama" as const,
    model: "gemma4:e2b",
    available: true,
    max_concurrent_requests: 1,
    num_ctx: 32768,
  },
  {
    id: "remote",
    name: "Research endpoint",
    type: "openai" as const,
    model: "analysis-model",
    available: true,
    max_concurrent_requests: 8,
  },
];

const meta = {
  title: "Corpus Builder/Setup/Enrichment Configuration",
  component: CorpusEnrichmentConfiguration,
  args: {
    selectedProviderId: "local",
    selectedReviewProviderId: "",
    providerProfiles: profiles,
    defaultProfileId: "local",
    selectedProviderLabel: "Local Ollama",
    selectedProfileModel: "gemma4:e2b",
    enrichmentMode: "fast",
    semanticIndexing: true,
    autoCleanText: true,
    llmTouchupDuringEnrichment: false,
    noiseUnusableThreshold: 45,
    llmAssessTextNoise: false,
    manualProvider: "ollama",
    manualModel: "",
    manualBaseUrl: "",
    manualApiKey: "",
    disabled: false,
  },
} satisfies Meta<typeof CorpusEnrichmentConfiguration>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Fast: Story = {};

export const Deep: Story = {
  args: {
    enrichmentMode: "deep",
    selectedReviewProviderId: "remote",
  },
};

export const ManualProvider: Story = {
  args: {
    selectedProviderId: "",
    selectedProviderLabel: "Ollama",
    selectedProfileModel: "",
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
