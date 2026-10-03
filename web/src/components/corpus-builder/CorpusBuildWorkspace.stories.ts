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
import CorpusBuildWorkspace from "./CorpusBuildWorkspace.vue";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Storybook fixture supplies only the fields the workspace reads.
const build: any = {
  build_id: "build-live-handoff",
  source_filename: "Of Grammatology.pdf",
  status: "running",
  stage: "enriching",
  progress: 0.58,
  record_count: 327,
  needs_review_count: 17,
  metadata_tasks_total: 981,
  metadata_tasks_completed: 552,
  metadata_tasks_running: 3,
  metadata_tasks_queued: 426,
  metadata_active_tasks: [
    { record_id: "record-184", task: "quotation", started_at: "2026-10-01T18:08:01Z" },
    { record_id: "record-185", task: "discourse", started_at: "2026-10-01T18:08:02Z" },
    { record_id: "record-186", task: "indexing", started_at: "2026-10-01T18:08:03Z" },
  ],
  build_events: [
    { at: "2026-10-01T18:00:00Z", stage: "preparing", status: "running", progress: 0.02 },
    {
      at: "2026-10-01T18:03:00Z",
      stage: "constructing_records",
      status: "running",
      progress: 0.36,
    },
    { at: "2026-10-01T18:08:00Z", stage: "enriching", status: "running", progress: 0.58 },
  ],
};

const meta = {
  title: "Corpus Builder/Build/Workspace",
  component: CorpusBuildWorkspace,
  args: {
    build,
    running: true,
    canResume: false,
    hasRecordTopology: true,
    readyCount: 36,
    enrichingCount: 3,
    preparingCount: 271,
    attentionCount: 17,
    awaitingManifestReview: false,
    retryingSegmentation: false,
    segmentationNeedsReview: false,
    contextSafe: true,
    providerLabel: "Local Ollama",
    modelLabel: "qwen3.5:4b",
  },
} satisfies Meta<typeof CorpusBuildWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ProgressiveEnrichment: Story = {};
