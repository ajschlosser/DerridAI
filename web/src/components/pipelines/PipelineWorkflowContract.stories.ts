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
import PipelineWorkflowContract from "./PipelineWorkflowContract.vue";
import type { PipelineDefinition } from "../../types/pipelines";
import { contractPurpose, contractVocabulary } from "./fixtures/pipelineCatalogContract";

const pipeline: PipelineDefinition = {
  pipeline_id: "evidence.reviewer.current",
  version: 2,
  name: "Evidence suggestion — reviewer support-gated",
  purpose: "evidence_suggestion",
  status: "active",
  entry_stage_ids: ["query"],
  stages: [],
  built_in: true,
};

const meta = {
  title: "Pipelines/Workflow Contract",
  component: PipelineWorkflowContract,
  args: {
    pipeline,
    purpose: contractPurpose("evidence_suggestion"),
    vocabulary: contractVocabulary,
  },
} satisfies Meta<typeof PipelineWorkflowContract>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ReviewerEvidence: Story = {};

export const Research: Story = {
  args: {
    pipeline: { ...pipeline, pipeline_id: "research.current", version: 1, purpose: "research" },
    purpose: contractPurpose("research"),
  },
};

export const VectorStoreSearch: Story = {
  args: {
    pipeline: {
      ...pipeline,
      pipeline_id: "store_search.similarity",
      version: 1,
      purpose: "vector_store_search",
    },
    purpose: contractPurpose("vector_store_search"),
  },
};

export const French: Story = { parameters: { locale: "fr-CA" } };
