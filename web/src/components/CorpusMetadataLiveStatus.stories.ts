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
import CorpusMetadataLiveStatus from "./CorpusMetadataLiveStatus.vue";

const build = {
  build_id: "build-1",
  asset_id: "asset-1",
  source_filename: "On Cosmopolitanism and Forgiveness.pdf",
  source_sha256: "abc",
  status: "running",
  stage: "enriching",
  progress: 0.52,
  created_at: new Date().toISOString(),
  record_count: 11,
  needs_review_count: 1,
  accepted_count: 0,
  profile_id: "derrida-scholarly-v12",
  metadata_enrichment_total: 11,
  metadata_concurrency: 3,
  metadata_tasks_total: 33,
  metadata_tasks_completed: 7,
  metadata_tasks_failed: 1,
  metadata_tasks_running: 3,
  metadata_tasks_queued: 22,
  metadata_last_progress_at: new Date().toISOString(),
  metadata_active_tasks: [
    {
      record_id: "derrida-cosmopoli-00001",
      task: "quotation",
      started_at: new Date().toISOString(),
    },
    {
      record_id: "derrida-cosmopoli-00002",
      task: "discourse",
      started_at: new Date().toISOString(),
    },
  ],
};
const meta = {
  title: "Corpus Builder/Status/Metadata Live Status",
  component: CorpusMetadataLiveStatus,
  args: { build },
} satisfies Meta<typeof CorpusMetadataLiveStatus>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Running: Story = {};
export const PartialFailure: Story = {
  args: {
    build: {
      ...build,
      metadata_tasks_completed: 18,
      metadata_tasks_failed: 3,
      metadata_tasks_running: 2,
      metadata_tasks_queued: 10,
    },
  },
};
export const Stalled: Story = {
  args: {
    build: {
      ...build,
      metadata_last_progress_at: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
    },
  },
};
export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    build: {
      ...build,
      source_filename: "Jacques Derrida — Cosmopolites de tous les pays, encore un effort !.pdf",
    },
  },
};
