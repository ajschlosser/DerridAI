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
import PipelineDefinitionHeader from "./PipelineDefinitionHeader.vue";
import type { PipelineDefinition } from "../../types/pipelines";
import {
  contractPurpose,
  contractPurposes,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";

const pipeline: PipelineDefinition = {
  pipeline_id: "research.current",
  version: 7,
  name: "Hybrid Research",
  purpose: "research",
  status: "active",
  entry_stage_ids: ["retrieve"],
  stages: [],
  built_in: true,
  validation: { valid: true, issues: [] },
  runtime_support: { supported: true, adapter: "research" },
};

const meta = {
  title: "Pipelines/Definition Header",
  component: PipelineDefinitionHeader,
  args: {
    pipeline,
    purpose: contractPurpose("research"),
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    assignment: null,
    assigned: true,
    canAssign: true,
    assigning: false,
    cloning: false,
  },
} satisfies Meta<typeof PipelineDefinitionHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ActiveAssignment: Story = {};

export const DraftInspectOnly: Story = {
  args: {
    pipeline: {
      ...pipeline,
      version: 8,
      status: "draft",
      runtime_support: { supported: false, reason: "The adapter cannot run this graph shape." },
    },
    assigned: false,
    canAssign: false,
  },
};

export const InvalidWithCustomAssignment: Story = {
  args: {
    pipeline: { ...pipeline, validation: { valid: false, issues: [] } },
    assigned: false,
    assignment: {
      feature: "research",
      pipeline_id: "research.custom",
      pipeline_version: 2,
      scope: "system",
      override_allowed: true,
      source: "system",
    },
  },
};
