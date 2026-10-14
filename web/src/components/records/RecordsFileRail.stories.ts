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
import RecordsFileRail from "./RecordsFileRail.vue";
import type { RecordsFileTab } from "../../domain/recordsFiles";

const files: RecordsFileTab[] = [
  {
    id: "jsonl-abc",
    name: "glas.jsonl",
    count: 412,
    dirty: 0,
    active: true,
    origin: "imported",
    origin_detail: "",
  },
  {
    id: "subset-1",
    name: "glas-primary-subset.jsonl",
    count: 206,
    dirty: 3,
    active: false,
    origin: "subset",
    origin_detail: "glas.jsonl",
  },
  {
    id: "chroma-1",
    name: "derrida-primary.jsonl",
    count: 12840,
    dirty: 0,
    active: false,
    origin: "chroma",
    origin_detail: "derrida-primary",
  },
];

const meta = {
  title: "Records/File Rail",
  component: RecordsFileRail,
  args: { files, canManage: true },
} satisfies Meta<typeof RecordsFileRail>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Populated: Story = {};
export const EditedSubset: Story = {
  args: {
    files: files.map((file) =>
      file.origin === "subset" ? { ...file, active: true } : { ...file, active: false },
    ),
  },
};
export const SingleImported: Story = {
  args: { files: [files[0]] },
};
