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
import { buildSemanticMap } from "../../domain/semanticMap";
import SemanticMapCanvas from "./SemanticMapCanvas.vue";

const graph = buildSemanticMap(
  [
    {
      id: "r1",
      work: "Of Grammatology",
      concepts: ["trace", "writing"],
      topics: ["presence"],
      persons: ["Rousseau"],
    },
  ],
  "r1",
);

const denseDisconnected = buildSemanticMap(
  Array.from({ length: 10 }, (_, index) => ({
    id: `record-${index}`,
    work: `Work ${index}`,
    concepts: [`concept ${index} alpha`, `concept ${index} beta`],
    topics: [`topic ${index}`],
    persons: [`Person ${index}`],
  })),
);

const meta = {
  title: "Corpus/Semantic map canvas",
  component: SemanticMapCanvas,
  args: { graph },
} satisfies Meta<typeof SemanticMapCanvas>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Draggable: Story = {};
export const DenseDisconnected: Story = {
  args: { graph: denseDisconnected },
};
export const DenseDisconnectedWide: Story = {
  args: { graph: denseDisconnected, density: "wide" },
};
