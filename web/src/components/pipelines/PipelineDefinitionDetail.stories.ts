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
import PipelineDefinitionDetail from "./PipelineDefinitionDetail.vue";
import type {
  PipelineAssignment,
  PipelineDefinition,
  PipelineStrategy,
} from "../../types/pipelines";
import {
  contractPurpose,
  contractPurposes,
  contractStrategy,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";

const strategies: PipelineStrategy[] = ["retrieve.chroma_similarity", "validate.provenance"].map(
  contractStrategy,
);

const pipeline: PipelineDefinition = {
  pipeline_id: "research.current",
  version: 1,
  name: "Research — current production chain",
  purpose: "research",
  status: "active",
  entry_stage_ids: ["retrieve"],
  built_in: true,
  stages: [
    {
      id: "retrieve",
      strategy: "retrieve.chroma_similarity",
      enabled: true,
      config: {},
      next: ["provenance"],
    },
    {
      id: "provenance",
      strategy: "validate.provenance",
      enabled: true,
      config: {},
      next: [],
    },
  ],
  validation: {
    valid: true,
    issues: [
      {
        level: "warning",
        code: "example",
        message: "Example warning shown for visual coverage.",
      },
    ],
  },
  runtime_support: { supported: true, adapter: "research" },
};

const assignment: PipelineAssignment = {
  feature: "research",
  pipeline_id: "research.current",
  pipeline_version: 1,
  scope: "system",
  scope_id: null,
  override_allowed: true,
  source: "built_in",
};

const meta = {
  title: "Pipelines/Definition Detail",
  component: PipelineDefinitionDetail,
  args: {
    pipeline,
    strategies,
    purpose: contractPurpose("research"),
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    assignment,
    assigned: true,
    canAssign: true,
    assigning: false,
    cloning: false,
  },
} satisfies Meta<typeof PipelineDefinitionDetail>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Assigned: Story = {};

export const InspectOnly: Story = {
  args: {
    assigned: false,
    canAssign: false,
    pipeline: {
      ...pipeline,
      status: "draft",
      runtime_support: {
        supported: false,
        adapter: null,
        reason: "This graph is inspectable but not executable by the current adapter.",
      },
    },
  },
};

export const FrenchContract: Story = {
  parameters: { locale: "fr-CA" },
};

export const UnregisteredPurpose: Story = {
  args: {
    purpose: null,
    assigned: false,
    canAssign: false,
    pipeline: { ...pipeline, purpose: "legacy_experiment", status: "draft" },
  },
};
