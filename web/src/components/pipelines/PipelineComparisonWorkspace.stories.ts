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
import PipelineComparisonWorkspace from "./PipelineComparisonWorkspace.vue";
import type { PipelineDefinition } from "../../types/pipelines";

const pipelines: PipelineDefinition[] = [
  {
    pipeline_id: "research.current",
    version: 1,
    name: "Research — current production chain",
    purpose: "research",
    status: "active",
    entry_stage_ids: ["query"],
    stages: [
      {
        id: "query",
        strategy: "query.research_decompose",
        enabled: true,
        config: {},
        next: ["dense"],
      },
      {
        id: "dense",
        strategy: "retrieve.chroma_similarity",
        enabled: true,
        config: { fetch_k: 500 },
        next: ["provenance"],
      },
      {
        id: "provenance",
        strategy: "validate.provenance",
        enabled: true,
        config: {},
        next: ["pack"],
      },
      {
        id: "pack",
        strategy: "pack.evidence_context",
        enabled: true,
        config: {},
        next: ["generate"],
      },
      {
        id: "generate",
        strategy: "llm.generate_answer",
        enabled: true,
        config: {},
        next: [],
      },
    ],
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
    stages: [
      {
        id: "query",
        strategy: "query.research_decompose",
        enabled: true,
        config: {},
        next: ["dense"],
      },
      {
        id: "dense",
        strategy: "retrieve.chroma_similarity",
        enabled: true,
        config: { fetch_k: 300 },
        next: ["provenance"],
      },
      {
        id: "provenance",
        strategy: "validate.provenance",
        enabled: true,
        config: {},
        next: ["pack"],
      },
      {
        id: "pack",
        strategy: "pack.evidence_context",
        enabled: true,
        config: {},
        next: ["generate"],
      },
      {
        id: "generate",
        strategy: "llm.generate_answer",
        enabled: true,
        config: {},
        next: [],
      },
    ],
    built_in: true,
    runtime_support: { supported: true, adapter: "research" },
  },
  {
    pipeline_id: "evidence.reviewer.current",
    version: 2,
    name: "Reviewer evidence — current",
    purpose: "evidence_suggestion",
    status: "active",
    entry_stage_ids: ["lexical"],
    stages: [],
    built_in: true,
    runtime_support: { supported: true, adapter: "evidence_suggestion" },
  },
  {
    pipeline_id: "evidence.lexical-only",
    version: 1,
    name: "Reviewer evidence — lexical",
    purpose: "evidence_suggestion",
    status: "draft",
    entry_stage_ids: ["lexical"],
    stages: [],
    runtime_support: { supported: true, adapter: "evidence_suggestion" },
  },
  {
    pipeline_id: "evidence.recovery.celf",
    version: 1,
    name: "Evidence recovery — cELF",
    purpose: "evidence_recovery",
    status: "active",
    entry_stage_ids: ["lexical"],
    stages: [],
    built_in: true,
    runtime_support: { supported: true, adapter: "evidence_recovery" },
  },
];

const meta = {
  title: "Pipelines/Comparison Workspace",
  component: PipelineComparisonWorkspace,
  args: { pipelines },
} satisfies Meta<typeof PipelineComparisonWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
