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
import CorpusSetupSection from "./CorpusSetupSection.vue";

const meta = {
  title: "Corpus Builder/Setup/Section",
  component: CorpusSetupSection,
  args: {
    id: "source",
    title: "Source",
    description: "Choose the document this build will read.",
    state: "complete",
    step: 1,
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
    step: 3,
    summary: "Scholarly default · 2 document fields need attention",
  },
};
export const Optional: Story = {
  args: {
    id: "advanced",
    title: "Advanced",
    state: "optional",
    step: undefined,
    summary: "Run policy defaults",
  },
};
export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    title: "Interprétation de la structure documentaire",
    summary:
      "Jacques Derrida — Cosmopolites de tous les pays, encore un effort ! — édition critique.pdf · PDF · 437 pages",
  },
};
