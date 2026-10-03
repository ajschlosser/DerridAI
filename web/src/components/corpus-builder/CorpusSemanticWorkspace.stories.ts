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
import CorpusSemanticWorkspace from "./CorpusSemanticWorkspace.vue";

const meta = {
  title: "Corpus Builder/Review/Semantic workspace",
  component: CorpusSemanticWorkspace,
  args: { buildId: "build-story", summary: { nodes: 1240, edges: 3810 } as never },
} satisfies Meta<typeof CorpusSemanticWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The closed state: one slim trigger with the graph size, in place of two disclosures. */
export const Closed: Story = {};

export const NoGraphYet: Story = { args: { summary: null } };

export const Disabled: Story = { args: { disabled: true } };
