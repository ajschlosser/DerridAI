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
import PipelineStageEditor from "./PipelineStageEditor.vue";
import type { PipelineStage, PipelineStrategy } from "../../types/pipelines";
import { contractStrategy, contractVocabulary } from "./fixtures/pipelineCatalogContract";

const stages: PipelineStage[] = [
  {
    id: "retrieve",
    strategy: "retrieve.chroma_similarity",
    enabled: true,
    config: { fetch_k: 500 },
    next: ["rerank"],
    on_empty: null,
    on_unavailable: null,
    on_timeout: null,
    on_error: null,
  },
  {
    id: "rerank",
    strategy: "rerank.cross_encoder",
    enabled: true,
    config: { top_k: 24 },
    next: [],
    on_empty: null,
    on_unavailable: "retrieve",
    on_timeout: "retrieve",
    on_error: "retrieve",
  },
];

const strategies: PipelineStrategy[] = ["retrieve.chroma_similarity", "rerank.cross_encoder"].map(
  contractStrategy,
);

const meta = {
  title: "Pipelines/Stage Editor",
  component: PipelineStageEditor,
  args: {
    stage: stages[0],
    stageIndex: 0,
    stages,
    strategies,
    entryStageIds: ["retrieve"],
    vocabulary: contractVocabulary,
  },
} satisfies Meta<typeof PipelineStageEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

export const RetrievalStage: Story = {};

export const CrossEncoderWithFallbacks: Story = {
  args: {
    stage: stages[1],
    stageIndex: 1,
    entryStageIds: ["retrieve"],
  },
};

const structuredMetadata: PipelineStrategy = contractStrategy("llm.structured_metadata");

const enrichmentStages: PipelineStage[] = [
  {
    id: "primary",
    strategy: "llm.structured_metadata",
    enabled: true,
    config: { provider_role: "primary", attempts: 2 },
    next: [],
    on_empty: null,
    on_unavailable: null,
    on_timeout: "review",
    on_error: "review",
  },
  {
    id: "review",
    strategy: "llm.structured_metadata",
    enabled: true,
    config: { provider_role: "review", attempts: 2 },
    next: [],
  },
];

export const StructuredMetadataWithEscalation: Story = {
  args: {
    stage: enrichmentStages[0],
    stageIndex: 0,
    stages: enrichmentStages,
    strategies: [structuredMetadata],
    entryStageIds: ["primary"],
  },
};
