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
import CorpusBuildPrimaryStatus from "./CorpusBuildPrimaryStatus.vue";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Storybook fixture supplies only the fields the status reads.
const build: any = {
  build_id: "build-42",
  source_filename: "Of Grammatology.pdf",
  status: "running",
  stage: "enriching",
  progress: 0.58,
  record_count: 327,
  needs_review_count: 0,
  metadata_tasks_total: 327,
  metadata_tasks_completed: 184,
  metadata_tasks_running: 3,
  metadata_active_tasks: [{ record_id: "rec_0184", task: "discourse" }],
};

const meta = {
  title: "Corpus Builder/Build/Primary Status",
  component: CorpusBuildPrimaryStatus,
  args: {
    build,
    running: true,
    canResume: false,
    hasRecordTopology: true,
    readyCount: 36,
    enrichingCount: 3,
    preparingCount: 271,
    attentionCount: 17,
    providerLabel: "Local Ollama",
    modelLabel: "qwen3.5:4b",
  },
} satisfies Meta<typeof CorpusBuildPrimaryStatus>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Enriching: Story = {};
export const Segmenting: Story = {
  args: {
    hasRecordTopology: false,
    build: {
      ...build,
      stage: "segmenting",
      progress: 0.27,
      record_count: 0,
      boundary_candidate_count: 247,
      boundary_candidates_completed: 83,
    },
  },
};
export const ReadyForReview: Story = {
  args: {
    running: false,
    build: {
      ...build,
      status: "awaiting_review",
      stage: "review",
      progress: 1,
      needs_review_count: 31,
    },
  },
};
export const Stopped: Story = {
  args: {
    running: false,
    canResume: true,
    build: { ...build, status: "failed", error: "The provider stopped responding." },
  },
};
export const Published: Story = {
  args: {
    running: false,
    build: {
      ...build,
      status: "published",
      stage: "published",
      progress: 1,
      publication: { publication_id: "publication-1" },
    },
  },
};
