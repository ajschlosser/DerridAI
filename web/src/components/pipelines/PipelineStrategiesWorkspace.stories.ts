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
import PipelineStrategiesWorkspace from "./PipelineStrategiesWorkspace.vue";
import type { PipelineDefinition } from "../../types/pipelines";
import {
  contractPurposes,
  contractStrategies,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";

const stage = (id: string, strategy: string) => ({
  id,
  strategy,
  enabled: true,
  config: {},
  next: [],
});

const pipelines: PipelineDefinition[] = [
  {
    pipeline_id: "research.current",
    version: 1,
    name: "Research — current production chain",
    purpose: "research",
    status: "active",
    entry_stage_ids: ["dense"],
    stages: [stage("dense", "retrieve.chroma_similarity"), stage("rerank", "rerank.cross_encoder")],
    built_in: true,
  },
  {
    pipeline_id: "evidence.reviewer.current",
    version: 2,
    name: "Evidence suggestion — reviewer support-gated",
    purpose: "evidence_suggestion",
    status: "active",
    entry_stage_ids: ["semantic"],
    stages: [
      stage("semantic", "retrieve.source_cosine"),
      stage("rerank", "rerank.cross_encoder"),
      stage("support", "validate.evidence_support"),
    ],
    built_in: true,
  },
];

const meta = {
  title: "Pipelines/Strategies Workspace",
  component: PipelineStrategiesWorkspace,
  args: {
    strategies: contractStrategies,
    pipelines,
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    selectedStrategyId: "rerank.cross_encoder",
    filters: {
      query: "",
      family: "",
      computation: "",
      capability: "",
      effect: "",
      workflow: "",
    },
  },
  render: (args) => ({
    components: { PipelineStrategiesWorkspace },
    setup() {
      const filters = ref({ ...args.filters });
      const selected = ref(args.selectedStrategyId);
      return { args, filters, selected };
    },
    template:
      '<PipelineStrategiesWorkspace v-bind="args" v-model:filters="filters" :selected-strategy-id="selected" @select-strategy="selected = $event" />',
  }),
} satisfies Meta<typeof PipelineStrategiesWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AllStrategies: Story = {};

export const French: Story = { parameters: { locale: "fr-CA" } };

export const FilteredByEffect: Story = {
  args: {
    filters: {
      query: "",
      family: "",
      computation: "deterministic",
      capability: "",
      effect: "provenance_gate",
      workflow: "",
    },
  },
};

export const Empty: Story = { args: { strategies: [] } };
