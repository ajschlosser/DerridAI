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
