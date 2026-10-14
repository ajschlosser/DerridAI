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
import PipelineExecutionList from "./PipelineExecutionList.vue";
import type { PipelineRunTrace } from "../../types/pipelines";
import { contractPurposes, contractVocabulary } from "./fixtures/pipelineCatalogContract";

const run = (id: string, status: string, feature: string): PipelineRunTrace => ({
  run_id: id,
  feature,
  pipeline_id: "research.current",
  pipeline_version: 7,
  resolved_pipeline: {},
  resolved_hash: "abc",
  status,
  started_at: "2026-09-30T08:31:00Z",
  total_elapsed_ms: 1730,
  stages: [],
});

const meta = {
  title: "Pipelines/Execution List",
  component: PipelineExecutionList,
  args: {
    runs: [
      run("rag-1", "completed", "research"),
      run("rag-2", "failed", "evidence_suggestion.reviewer"),
      run("rag-3", "running", "research"),
    ],
    pipelines: [],
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    selectedRunId: "rag-2",
    total: 3,
    limit: 25,
    offset: 0,
  },
} satisfies Meta<typeof PipelineExecutionList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
