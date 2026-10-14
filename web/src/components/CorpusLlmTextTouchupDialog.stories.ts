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
import type { ProviderProfile } from "../api/system";
import CorpusLlmTextTouchupDialog from "./CorpusLlmTextTouchupDialog.vue";
const meta = {
  title: "Corpus Builder/Review/LLM Text Touch-up",
  component: CorpusLlmTextTouchupDialog,
  args: {
    open: true,
    profiles: [
      {
        id: "primary",
        name: "Local scholarly",
        type: "ollama",
        model: "gemma4:e4b",
      } as ProviderProfile,
    ],
    providerProfileId: "primary",
    recordId: "r1",
    sourceText:
      "This is a sentence\nbroken by PDF layout.  It has OCR artefacts ﬁ and odd spacing.",
    proposedText:
      "This is a sentence broken by PDF layout. It has OCR artefacts fi and odd spacing.",
    changes: ["Joined an accidental line wrap", "Normalized an OCR ligature"],
    warnings: [],
    model: "gemma4:e4b",
  },
} satisfies Meta<typeof CorpusLlmTextTouchupDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Proposal: Story = {};
export const WithWarning: Story = {
  args: { warnings: ["A possible authorial spelling was left unchanged."] },
};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
