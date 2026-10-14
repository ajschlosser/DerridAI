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
import CorpusBuildTimeline from "./CorpusBuildTimeline.vue";
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
const build: any = {
  build_id: "build-aardvark",
  asset_id: "asset",
  source_filename: "book.pdf",
  source_sha256: "sha",
  status: "awaiting_metadata",
  stage: "metadata_review",
  progress: 0.96,
  created_at: "",
  record_count: 63,
  needs_review_count: 0,
  accepted_count: 63,
  profile_id: "derrida-scholarly-v8",
  build_events: [
    { at: "2026-09-17T18:00:00Z", stage: "structure", status: "running", progress: 0.05 },
    { at: "2026-09-17T18:02:00Z", stage: "segmenting", status: "running", progress: 0.18 },
    { at: "2026-09-17T18:04:00Z", stage: "enriching", status: "running", progress: 0.42 },
    { at: "2026-09-17T18:12:00Z", stage: "review", status: "awaiting_review", progress: 0.9 },
    {
      at: "2026-09-17T18:30:00Z",
      stage: "metadata_review",
      status: "awaiting_metadata",
      progress: 0.96,
    },
  ],
};
const meta = {
  title: "Corpus Builder/Workflow/Build Timeline",
  component: CorpusBuildTimeline,
  args: { build },
} satisfies Meta<typeof CorpusBuildTimeline>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
