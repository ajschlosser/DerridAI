/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import PipelineDefinitionEditor from "./PipelineDefinitionEditor.vue";
import type { PipelineDefinition, PipelineStrategy } from "../../types/pipelines";
import { contractStrategy } from "./fixtures/pipelineCatalogContract";

const strategies: PipelineStrategy[] = [
  "retrieve.chroma_similarity",
  "select.source_diversity",
].map(contractStrategy);

const pipeline: PipelineDefinition = {
  pipeline_id: "research.custom",
  version: 3,
  name: "Research — source-diverse",
  purpose: "research",
  status: "draft",
  entry_stage_ids: ["dense"],
  stages: [
    {
      id: "dense",
      strategy: "retrieve.chroma_similarity",
      enabled: true,
      config: { fetch_k: 500 },
      next: ["diversity"],
    },
    {
      id: "diversity",
      strategy: "select.source_diversity",
      enabled: true,
      config: { limit: 24 },
      next: [],
    },
  ],
  built_in: false,
  notes: "Tune on the fixed DerridAI retrieval benchmark before activation.",
};

const meta = {
  title: "Pipelines/Definition Editor",
  component: PipelineDefinitionEditor,
  args: {
    modelValue: pipeline,
    strategies,
  },
  render: (args) => ({
    components: { PipelineDefinitionEditor },
    setup() {
      const value = ref(structuredClone(args.modelValue));
      return { args, value };
    },
    template:
      '<PipelineDefinitionEditor v-model="value" :strategies="args.strategies" style="max-width: 820px" />',
  }),
} satisfies Meta<typeof PipelineDefinitionEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

export const DraftVersion: Story = {};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
