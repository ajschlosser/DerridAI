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
