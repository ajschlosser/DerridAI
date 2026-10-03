/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
    documentIntelligenceProfile: "scholarly",
    documentNlpProvider: "auto",
    documentNlpIncludeEvents: false,
    autoCleanText: false,
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

export const FictionDocumentIntelligence: Story = {
  args: {
    documentIntelligenceProfile: "fiction",
    documentNlpProvider: "booknlp",
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
