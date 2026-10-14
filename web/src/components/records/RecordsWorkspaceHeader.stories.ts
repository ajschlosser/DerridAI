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
import RecordsWorkspaceHeader from "./RecordsWorkspaceHeader.vue";

const meta = {
  title: "Records/Workspace Header",
  component: RecordsWorkspaceHeader,
  args: {
    fileName: "ear-of-the-other_corpus-subset-primary.jsonl",
    matched: 206,
    total: 206,
    flagged: 0,
    selected: 3,
  },
} satisfies Meta<typeof RecordsWorkspaceHeader>;
export default meta;
type Story = StoryObj<typeof RecordsWorkspaceHeader>;
export const Default: Story = {};
export const Empty: Story = {
  args: { fileName: "", matched: 0, total: 0, flagged: 0, selected: 0 },
};

export const InitialRead: Story = { args: { ready: false } };
