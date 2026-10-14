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
import PipelineVersionEditorPanel from "./PipelineVersionEditorPanel.vue";
import type { PipelineDefinition } from "../../types/pipelines";
import {
  contractPurpose,
  contractStrategies,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";

const draft: PipelineDefinition = {
  pipeline_id: "evidence.reviewer.current.custom",
  version: 1,
  name: "Evidence suggestion — reviewer support-gated — custom",
  purpose: "evidence_suggestion",
  status: "draft",
  entry_stage_ids: ["semantic"],
  stages: [
    {
      id: "semantic",
      strategy: "retrieve.source_cosine",
      enabled: true,
      config: {},
      next: ["support"],
    },
    { id: "support", strategy: "validate.evidence_support", enabled: true, config: {}, next: [] },
  ],
  derived_from: "evidence.reviewer.current@2",
};

const meta = {
  title: "Pipelines/Version Editor Panel",
  component: PipelineVersionEditorPanel,
  args: {
    modelValue: draft,
    strategies: contractStrategies,
    purpose: contractPurpose("evidence_suggestion"),
    vocabulary: contractVocabulary,
    validation: null,
    saving: false,
  },
  render: (args) => ({
    components: { PipelineVersionEditorPanel },
    setup() {
      const value = ref<PipelineDefinition>(JSON.parse(JSON.stringify(args.modelValue)));
      return { args, value };
    },
    template:
      '<PipelineVersionEditorPanel v-model="value" :strategies="args.strategies" :purpose="args.purpose" :vocabulary="args.vocabulary" :validation="args.validation" :saving="args.saving" />',
  }),
} satisfies Meta<typeof PipelineVersionEditorPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ReviewerEvidenceClone: Story = {};

export const InspectOnlyStage: Story = {
  args: {
    modelValue: {
      ...draft,
      stages: [
        { ...draft.stages[0], next: ["source-diversity"] },
        {
          id: "source-diversity",
          strategy: "select.source_diversity",
          enabled: true,
          config: {},
          next: [],
        },
      ],
    },
  },
};

export const French: Story = { parameters: { locale: "fr-CA" } };
