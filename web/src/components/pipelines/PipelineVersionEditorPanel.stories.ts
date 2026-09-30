/* Copyright 2026 Aaron John Schlosser, PhD. */
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
        { ...draft.stages[0], next: ["mmr"] },
        { id: "mmr", strategy: "select.mmr", enabled: true, config: {}, next: [] },
      ],
    },
  },
};

export const French: Story = { parameters: { locale: "fr-CA" } };
