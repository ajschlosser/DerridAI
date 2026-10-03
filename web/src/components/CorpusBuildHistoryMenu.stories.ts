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
import CorpusBuildHistoryMenu from "./CorpusBuildHistoryMenu.vue";
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
const builds: any[] = [
  {
    build_id: "b1",
    source_filename: "On Cosmopolitanism and Forgiveness.pdf",
    status: "running",
    stage: "enriching",
    progress: 0.62,
    record_count: 31,
    created_at: new Date().toISOString(),
  },
  {
    build_id: "b2",
    source_filename: "Rogues.pdf",
    status: "ready",
    stage: "ready",
    progress: 1,
    record_count: 82,
    created_at: new Date().toISOString(),
  },
];
const meta = {
  title: "Corpus Builder/Workflow/Build History Menu",
  component: CorpusBuildHistoryMenu,
  args: { builds, total: 2, selectedBuildId: "b1" },
} satisfies Meta<typeof CorpusBuildHistoryMenu>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
