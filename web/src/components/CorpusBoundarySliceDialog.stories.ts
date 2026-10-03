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
import CorpusBoundarySliceDialog from "./CorpusBoundarySliceDialog.vue";
const text =
  "This sentence belongs to the previous record and was cut at the wrong boundary. This sentence begins the actual current record and should remain here.";
const meta = {
  title: "Corpus Builder/Review/Boundary Slice Dialog",
  component: CorpusBoundarySliceDialog,
  args: { text, canPrevious: true, canNext: true },
} satisfies Meta<typeof CorpusBoundarySliceDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const NoPrevious: Story = { args: { canPrevious: false } };
