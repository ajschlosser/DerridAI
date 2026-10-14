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
import CorpusRecordResearchClaims from "./CorpusRecordResearchClaims.vue";

const meta: Meta<typeof CorpusRecordResearchClaims> = {
  title: "Corpus Builder/Review/Research Claims",
  component: CorpusRecordResearchClaims,
  args: {
    buildId: "build-1",
    recordId: "r-7",
    load: async () => ({
      items: [
        {
          claim_id: "c-1",
          claim_text: "Unconditional hospitality exceeds every law of hospitality.",
          relation: "supports",
          record_revision: 4,
          validated_by: "ann",
          citation: { inline: "(Derrida, Of Hospitality, 25)" },
          binding_status: "current",
        },
        {
          claim_id: "c-2",
          claim_text: "The host becomes hostage.",
          relation: "contextualizes",
          record_revision: 2,
          validated_by: "ann",
          citation: {},
          binding_status: "stale",
        },
      ],
    }),
  },
};
export default meta;
type Story = StoryObj<typeof CorpusRecordResearchClaims>;
export const Default: Story = {};
export const None: Story = { args: { load: async () => ({ items: [] }) } };
