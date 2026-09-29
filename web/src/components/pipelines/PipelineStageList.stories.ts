/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineStageList from "./PipelineStageList.vue";
import type { PipelineDefinition, PipelineStrategy } from "../../types/pipelines";

const strategies: PipelineStrategy[] = [
  {
    strategy_id: "retrieve.chroma_similarity",
    version: 1,
    family: "candidate_generation",
    label: "Chroma semantic similarity",
    description: "Retrieve nearest candidates from a compatible Chroma collection.",
    input_type: "query",
    output_type: "candidate_set",
    deterministic: false,
    invokes_llm: false,
    capabilities: ["embedding", "chroma"],
    config_schema: {
      type: "object",
      properties: { fetch_k: { type: "integer", minimum: 1, maximum: 5000 } },
    },
  },
  {
    strategy_id: "rerank.cross_encoder",
    version: 1,
    family: "rerank",
    label: "Cross-encoder reranker",
    description: "Score query/candidate pairs with the shared cross-encoder boundary.",
    input_type: "candidate_set",
    output_type: "candidate_set",
    deterministic: false,
    invokes_llm: false,
    capabilities: ["cross_encoder"],
    config_schema: { type: "object", properties: {} },
  },
  {
    strategy_id: "llm.generate_answer",
    version: 1,
    family: "llm",
    label: "Research answer generation",
    description: "Generate the evidence-grounded Research answer.",
    input_type: "context_packet",
    output_type: "model_output",
    deterministic: false,
    invokes_llm: true,
    capabilities: ["chat_model"],
    config_schema: { type: "object", properties: {} },
  },
];

const pipeline: PipelineDefinition = {
  pipeline_id: "research.example",
  version: 2,
  name: "Research example",
  purpose: "research",
  status: "active",
  entry_stage_ids: ["dense"],
  stages: [
    {
      id: "dense",
      strategy: "retrieve.chroma_similarity",
      enabled: true,
      config: { fetch_k: 500 },
      next: ["rerank"],
    },
    {
      id: "rerank",
      strategy: "rerank.cross_encoder",
      enabled: true,
      config: {},
      next: ["generate"],
      on_unavailable: "generate",
    },
    {
      id: "generate",
      strategy: "llm.generate_answer",
      enabled: true,
      config: {},
      next: [],
    },
  ],
};

const meta = {
  title: "Pipelines/Stage List",
  component: PipelineStageList,
  args: { pipeline, strategies },
} satisfies Meta<typeof PipelineStageList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
