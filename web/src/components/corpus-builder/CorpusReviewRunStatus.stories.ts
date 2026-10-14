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
import CorpusReviewRunStatus from "./CorpusReviewRunStatus.vue";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Storybook fixture intentionally supplies only fields used by the monitor and its child status surfaces.
const build: any = {
  build_id: "build-42",
  asset_id: "asset-1",
  source_filename: "Of Grammatology.pdf",
  source_sha256: "abc123",
  status: "running",
  stage: "enriching",
  progress: 0.58,
  created_at: "2026-09-25T18:00:00Z",
  started_at: "2026-09-25T18:01:00Z",
  record_count: 48,
  needs_review_count: 9,
  accepted_count: 14,
  provider: "ollama",
  model: "qwen3.5:4b",
  provider_profile_history: [],
  metadata_enrichment_total: 48,
  metadata_tasks_total: 96,
  metadata_tasks_completed: 54,
  metadata_tasks_running: 2,
  metadata_tasks_queued: 40,
  metadata_tasks_failed: 0,
  metadata_last_progress_at: "2026-09-25T18:14:00Z",
  metadata_operation: {
    state: "running",
  },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Sparse provider fixtures make the story resilient to unrelated provider-profile additions.
const profiles: any[] = [
  {
    id: "local-qwen",
    name: "Local Qwen",
    type: "ollama",
    model: "qwen3.5:4b",
    available: true,
  },
  {
    id: "local-gemma",
    name: "Local Gemma",
    type: "ollama",
    model: "gemma4:e4b",
    available: true,
  },
];

const meta = {
  title: "Corpus Builder/Review/Run Status",
  component: CorpusReviewRunStatus,
  args: {
    build,
    profiles,
    activeProfileId: "local-qwen",
    activeModel: "qwen3.5:4b",
  },
} satisfies Meta<typeof CorpusReviewRunStatus>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = {};

export const Warning: Story = {
  args: {
    build: {
      ...build,
      warnings: [
        "One enrichment task was retried after a provider timeout.",
        "Nine records still require human review.",
      ],
      metadata_tasks_failed: 1,
    },
  },
};

export const Completed: Story = {
  args: {
    build: {
      ...build,
      status: "awaiting_review",
      stage: "review",
      progress: 1,
      metadata_operation: { state: "complete" },
      metadata_tasks_completed: 96,
      metadata_tasks_running: 0,
      metadata_tasks_queued: 0,
      finished_at: "2026-09-25T18:22:00Z",
    },
  },
};

export const Failed: Story = {
  args: {
    build: {
      ...build,
      status: "failed",
      stage: "enriching",
      progress: 0.63,
      error: "The active provider stopped responding during metadata enrichment.",
      metadata_operation: { state: "failed" },
    },
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    build: {
      ...build,
      source_filename:
        "Jacques Derrida — Cosmopolites de tous les pays, encore un effort ! — édition critique.pdf",
      warnings: [
        "Certaines métadonnées nécessitent encore une vérification humaine avant la publication.",
      ],
    },
  },
};
