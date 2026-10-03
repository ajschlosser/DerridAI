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
import SemanticMapFrame from "./SemanticMapFrame.vue";

const sources = [
  {
    id: "r1",
    work: "Of Grammatology",
    concepts: ["trace", "writing"],
    topics: ["presence"],
    persons: ["Rousseau"],
  },
  {
    id: "r2",
    work: "Writing and Difference",
    concepts: ["trace", "différance"],
    topics: ["presence"],
    persons: ["Levinas"],
  },
];

const meta = {
  title: "Corpus/Semantic map",
  component: SemanticMapFrame,
  args: { variant: "page", sources, focusId: "r1", showClose: false },
} satisfies Meta<typeof SemanticMapFrame>;
export default meta;
type Story = StoryObj<typeof meta>;

export const DedicatedView: Story = {};
export const AboveRecord: Story = { args: { variant: "record", showClose: true } };
export const Sidebar: Story = { args: { variant: "sidebar" } };
export const Dialog: Story = { args: { variant: "modal" } };
export const Empty: Story = { args: { sources: [], focusId: "" } };
