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
import CompareDiff from "./CompareDiff.vue";
import { buildCompareRows } from "../../domain/compare";

const rows = buildCompareRows(
  { record_id: "r-a", work: "Glas", text: "the gift of death" },
  { record_id: "r-a", work: "Glas", text: "the gift of life" },
  "changed",
).map((row) => ({ ...row, label: row.key === "text" ? "Text" : row.key }));

const meta = {
  title: "Compare/Diff",
  component: CompareDiff,
  args: {
    rows,
    emptyLabel: "These records are identical across all compared fields.",
    changedLabel: "Changed",
    identicalLabel: "Identical",
    sideA: "Record A",
    sideB: "Record B",
  },
} satisfies Meta<typeof CompareDiff>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Changed: Story = {};
export const Identical: Story = { args: { rows: [] } };
