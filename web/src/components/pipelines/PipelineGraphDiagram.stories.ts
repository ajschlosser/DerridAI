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
import PipelineGraphDiagram from "./PipelineGraphDiagram.vue";
import { contractStrategies } from "./fixtures/pipelineCatalogContract";
import type { PipelineStage } from "../../types/pipelines";

const stage = (id: string, strategy: string, next: string[] = []): PipelineStage => ({
  id,
  strategy,
  enabled: true,
  config: {},
  next,
});

const stages: PipelineStage[] = [
  stage("dense", "retrieve.chroma_similarity", ["lexical"]),
  stage("lexical", "retrieve.lexical_bm25", ["pick"]),
  stage("pick", "select.top_k"),
];

const meta = {
  title: "Pipelines/Graph Diagram",
  component: PipelineGraphDiagram,
  args: {
    stages,
    entryStageIds: ["dense"],
    strategies: contractStrategies,
    title: "Pipeline diagram",
    description: "Focus or hover a stage to see the data type its connections carry.",
    showInspector: false,
  },
} satisfies Meta<typeof PipelineGraphDiagram>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Plain: Story = {};

/** `dense → lexical` only runs the first stage ahead of a binding; it carries no data. */
export const OrderingOnlyEdge: Story = {
  args: { orderingEdges: [{ from: "dense", to: "lexical" }] },
};
