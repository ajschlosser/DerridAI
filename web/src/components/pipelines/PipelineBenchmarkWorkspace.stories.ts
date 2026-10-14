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
import type { PipelineDefinition } from "../../types/pipelines";
import PipelineBenchmarkWorkspace from "./PipelineBenchmarkWorkspace.vue";

const pipelines: PipelineDefinition[] = [
  {
    pipeline_id: "research.current",
    version: 1,
    name: "Research — current production chain",
    purpose: "research",
    status: "active",
    entry_stage_ids: ["query"],
    stages: [],
    built_in: true,
    runtime_support: { supported: true, adapter: "research" },
  },
  {
    pipeline_id: "research.balanced",
    version: 1,
    name: "Research — balanced",
    purpose: "research",
    status: "draft",
    entry_stage_ids: ["query"],
    stages: [],
    built_in: true,
    runtime_support: { supported: true, adapter: "research" },
  },
];

const meta = {
  title: "Pipelines/Benchmark Workspace",
  component: PipelineBenchmarkWorkspace,
  args: { pipelines },
} satisfies Meta<typeof PipelineBenchmarkWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
