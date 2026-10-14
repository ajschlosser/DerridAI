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
import SemanticGraphEntityIndex from "./SemanticGraphEntityIndex.vue";

const items = Array.from({ length: 8 }, (_, i) => ({
  id: `n${i}`,
  type: i % 2 ? "person" : "concept",
  label: `Entity ${i + 1}`,
  aliases: i % 3 ? [] : ["alias one", "alias two"],
  mention_count: 100 - i,
  record_count: 4,
  degree: 3,
}));

const meta = {
  title: "Corpus Builder/Review/Semantic Entity Index",
  component: SemanticGraphEntityIndex,
  args: {
    nodeTotal: 240,
    index: { total: 240, offset: 0, limit: 50, sort: "mentions" as const, items },
    loading: false,
    selectedNodeId: "n2",
    hueClass: (type: string) => (type === "person" ? "hue-2" : "hue-1"),
    sort: "mentions" as const,
    offset: 0,
  },
} satisfies Meta<typeof SemanticGraphEntityIndex>;

export default meta;
type Story = StoryObj<typeof meta>;

export const FirstPage: Story = {};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
