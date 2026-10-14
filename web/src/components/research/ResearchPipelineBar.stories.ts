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
import ResearchPipelineBar from "./ResearchPipelineBar.vue";
const meta: Meta<typeof ResearchPipelineBar> = {
  title: "Research/Pipeline Bar",
  component: ResearchPipelineBar,
  args: {
    selectedJobId: "rag-2",
    canManage: true,
    jobs: [
      {
        id: "rag-1",
        status: "running",
        prompt: "How does Derrida distinguish responsibility from duty?",
        stage_detail: "Reranking evidence",
        model: "qwen3",
      },
      {
        id: "rag-2",
        status: "queued",
        prompt: "Compare hospitality in Adieu and Of Hospitality",
        stage_detail: "Waiting for provider capacity",
        model: "phi4",
      },
      {
        id: "rag-3",
        status: "running",
        prompt: "Trace Derrida's use of the gift",
        stage_detail: "Generating answer",
        model: "gpt-oss",
      },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof ResearchPipelineBar>;
export const MultipleConcurrentRuns: Story = {};
