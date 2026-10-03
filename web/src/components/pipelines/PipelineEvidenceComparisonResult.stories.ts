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
import PipelineEvidenceComparisonResult from "./PipelineEvidenceComparisonResult.vue";
import type { EvidencePipelineComparisonResult } from "../../types/pipelines";

const result: EvidencePipelineComparisonResult = {
  non_persistent: true,
  left: {
    pipeline: {
      pipeline_id: "evidence.reviewer.current",
      pipeline_version: 2,
      pipeline_hash: "left",
      purpose: "evidence_suggestion",
    },
    elapsed_seconds: 0.12,
    stages: [],
    candidates: [
      { block_id: "b1", rank: 1, score: 0.9 },
      { block_id: "b2", rank: 2, score: 0.4 },
    ],
  },
  right: {
    pipeline: {
      pipeline_id: "evidence.lexical-only",
      pipeline_version: 1,
      pipeline_hash: "right",
      purpose: "evidence_suggestion",
    },
    elapsed_seconds: 0.08,
    stages: [],
    candidates: [{ block_id: "b1", rank: 1, score: 0.7 }],
  },
  comparison: {
    shared_block_ids: ["b1"],
    left_only_block_ids: ["b2"],
    right_only_block_ids: [],
    shared_count: 1,
    union_count: 2,
    jaccard_overlap: 0.5,
    rank_changes: [{ block_id: "b1", left_rank: 1, right_rank: 1, rank_delta: 0 }],
    elapsed_seconds_delta: -0.04,
  },
};

const meta = {
  title: "Pipelines/Evidence Comparison Result",
  component: PipelineEvidenceComparisonResult,
  args: { result },
} satisfies Meta<typeof PipelineEvidenceComparisonResult>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
