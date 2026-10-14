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
import CorpusLlmEffectivenessPanel from "./CorpusLlmEffectivenessPanel.vue";
const familyEffectiveness = {
  discourse: {
    calls: 10,
    proposed_fields: 18,
    human_accepted_fields: 7,
    human_corrected_fields: 2,
  },
  quotation: { calls: 5, proposed_fields: 2, human_accepted_fields: 1, human_corrected_fields: 0 },
  indexing: { calls: 3, proposed_fields: 0, human_accepted_fields: 0, human_corrected_fields: 0 },
};
const confidenceCalibration = {
  discourse_role: {
    high: { reviewed: 14, accepted: 12, corrected: 2, acceptance_rate: 0.857 },
    medium: { reviewed: 8, accepted: 5, corrected: 3, acceptance_rate: 0.625 },
  },
};
const modelEffectiveness = {
  gemma: { model: "gemma4:e4b", calls: 12, proposed_fields: 20, elapsed_ms: 240000 },
  qwen: { model: "Qwen3.8-27B", calls: 6, proposed_fields: 8, elapsed_ms: 72000 },
};
const meta = {
  title: "Corpus Builder/Review/Automation Effectiveness",
  component: CorpusLlmEffectivenessPanel,
  args: {
    contribution: {
      family_calls: 18,
      elapsed_ms: 312000,
      llm_fields_usable: 26,
      llm_fields_proposed: 7,
      llm_fields_review: 7,
      inherited_fields: 74,
      deterministic_fields: 33,
      human_fields: 15,
      useful_fields_per_minute: 5,
    },
    editorialExamplesUsed: 9,
    familyEffectiveness,
    confidenceCalibration,
    modelEffectiveness,
  },
} satisfies Meta<typeof CorpusLlmEffectivenessPanel>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Useful: Story = {};
export const NoUsefulFieldsYet: Story = {
  args: {
    contribution: {
      family_calls: 7,
      elapsed_ms: 180000,
      llm_fields_usable: 0,
      llm_fields_proposed: 0,
      llm_fields_review: 4,
      useful_fields_per_minute: 0,
    },
  },
};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
