/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import PipelineDefinitionEditor from "./PipelineDefinitionEditor.vue";
import type { PipelineDefinition, PipelineStrategy } from "../../types/pipelines";

const strategies: PipelineStrategy[] = [
  {
    strategy_id: "retrieve.chroma_similarity",
    version: 1,
    family: "candidate_generation",
    label: "Chroma semantic similarity",
    description: "Retrieve nearest candidates from the configured collection.",
    input_type: "query",
    output_type: "candidate_set",
    deterministic: false,
    invokes_llm: false,
    capabilities: ["embedding", "chroma"],
    config_schema: {
      type: "object",
      properties: {
        fetch_k: { type: "integer", minimum: 1, maximum: 5000 },
      },
    },
  },
  {
    strategy_id: "select.source_diversity",
    version: 1,
    family: "diversity",
    label: "Source-aware diversity",
    description: "Avoid redundant adjacent context after relevance reranking.",
    input_type: "candidate_set",
    output_type: "candidate_set",
    deterministic: true,
    invokes_llm: false,
    capabilities: [],
    config_schema: {
      type: "object",
      properties: {
        limit: { type: "integer", minimum: 1, maximum: 500 },
      },
    },
  },
];

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
