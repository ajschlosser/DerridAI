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
import { ref } from "vue";
import PipelineDefinitionNavigator from "./PipelineDefinitionNavigator.vue";
import type { PipelineAssignment, PipelineDefinition } from "../../types/pipelines";
import { contractPurposes, contractVocabulary } from "./fixtures/pipelineCatalogContract";

const pipelines: PipelineDefinition[] = [
  {
    pipeline_id: "research.current",
    version: 1,
    name: "Research — current production chain",
    purpose: "research",
    status: "active",
    entry_stage_ids: ["retrieve"],
    stages: [],
    built_in: true,
  },
  {
    pipeline_id: "research.experimental",
    version: 3,
    name: "Research — experimental source-diverse",
    purpose: "research",
    status: "draft",
    entry_stage_ids: ["retrieve"],
    stages: [],
    built_in: false,
  },
  {
    pipeline_id: "evidence.reviewer.current",
    version: 2,
    name: "Evidence suggestion — reviewer support-gated",
    purpose: "evidence_suggestion",
    status: "active",
    entry_stage_ids: ["query"],
    stages: [],
    built_in: true,
  },
  {
    pipeline_id: "evidence.recovery.cascade",
    version: 1,
    name: "Evidence recovery — relevance cascade",
    purpose: "evidence_recovery",
    status: "active",
    entry_stage_ids: ["query"],
    stages: [],
    built_in: true,
  },
  {
    pipeline_id: "store_search.similarity",
    version: 1,
    name: "Vector Store search — similarity",
    purpose: "vector_store_search",
    status: "active",
    entry_stage_ids: ["query"],
    stages: [],
    built_in: true,
  },
  {
    pipeline_id: "metadata.precedents.current",
    version: 1,
    name: "Metadata precedents — current",
    purpose: "metadata_precedents",
    status: "active",
    entry_stage_ids: ["retrieve"],
    stages: [],
    built_in: true,
  },
];

const assignments: PipelineAssignment[] = [
  {
    feature: "research",
    pipeline_id: "research.current",
    pipeline_version: 1,
    scope: "system",
    scope_id: null,
    override_allowed: true,
    source: "built_in",
  },
];

const meta = {
  title: "Pipelines/Definition Navigator",
  component: PipelineDefinitionNavigator,
  args: {
    pipelines,
    assignments,
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    selectedKey: "research.current@1",
    workflow: "",
  },
  render: (args) => ({
    components: { PipelineDefinitionNavigator },
    setup() {
      const filters = ref({ query: "", status: "" });
      const workflow = ref(args.workflow || "");
      const selected = ref(args.selectedKey);
      return { args, filters, workflow, selected };
    },
    template:
      '<PipelineDefinitionNavigator v-bind="args" v-model:filters="filters" v-model:workflow="workflow" :selected-key="selected" @select="selected = $event" />',
  }),
} satisfies Meta<typeof PipelineDefinitionNavigator>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const MultipleVersions: Story = {
  args: {
    pipelines: [
      ...pipelines,
      { ...pipelines[0], version: 2, status: "active", name: pipelines[0].name },
      { ...pipelines[0], version: 3, status: "draft", name: pipelines[0].name },
    ],
    selectedKey: "research.current@2",
  },
};

export const EvidenceWorkflow: Story = {
  args: { workflow: "evidence", selectedKey: "evidence.reviewer.current@2" },
};

export const LongNamesAndFrench: Story = {
  args: {
    pipelines: pipelines.map((pipeline) => ({
      ...pipeline,
      name: `${pipeline.name} — configuration de récupération et validation avec un intitulé long`,
    })),
  },
  parameters: { locale: "fr-CA" },
};
