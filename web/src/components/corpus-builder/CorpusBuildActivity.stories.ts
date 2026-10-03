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
import CorpusBuildActivity from "./CorpusBuildActivity.vue";

const build = {
  build_id: "build-live",
  status: "running",
  stage: "enriching",
  progress: 0.64,
  record_count: 42,
  build_events: [
    { at: "2026-09-30T18:00:00Z", stage: "preparing", status: "running", progress: 0.02 },
    { at: "2026-09-30T18:01:00Z", stage: "structure", status: "running", progress: 0.12 },
    {
      at: "2026-09-30T18:03:00Z",
      stage: "constructing_records",
      status: "running",
      progress: 0.36,
    },
    { at: "2026-09-30T18:05:00Z", stage: "enriching", status: "running", progress: 0.64 },
  ],
} as never;

const meta = {
  title: "Corpus Builder/Build/Activity",
  component: CorpusBuildActivity,
  args: { build },
} satisfies Meta<typeof CorpusBuildActivity>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Live: Story = {};
