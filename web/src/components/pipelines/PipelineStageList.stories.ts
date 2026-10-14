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
import PipelineStageList from "./PipelineStageList.vue";
import type { PipelineDefinition, PipelineStrategy } from "../../types/pipelines";
import { contractStrategy } from "./fixtures/pipelineCatalogContract";

const strategies: PipelineStrategy[] = [
  "retrieve.chroma_similarity",
  "rerank.cross_encoder",
  "llm.generate_answer",
].map(contractStrategy);

const pipeline: PipelineDefinition = {
  pipeline_id: "research.example",
  version: 2,
  name: "Research example",
  purpose: "research",
  status: "active",
  entry_stage_ids: ["dense"],
  stages: [
    {
      id: "dense",
      strategy: "retrieve.chroma_similarity",
      enabled: true,
      config: { fetch_k: 500 },
      next: ["rerank"],
    },
    {
      id: "rerank",
      strategy: "rerank.cross_encoder",
      enabled: true,
      config: {},
      next: ["generate"],
      on_unavailable: "generate",
    },
    {
      id: "generate",
      strategy: "llm.generate_answer",
      enabled: true,
      config: {},
      next: [],
    },
  ],
};

const meta = {
  title: "Pipelines/Stage List",
  component: PipelineStageList,
  args: { pipeline, strategies },
} satisfies Meta<typeof PipelineStageList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
