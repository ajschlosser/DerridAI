/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineStageEditor from "./PipelineStageEditor.vue";
import type { PipelineStage, PipelineStrategy } from "../../types/pipelines";

const stages: PipelineStage[] = [
  {
    id: "retrieve",
    strategy: "retrieve.chroma_similarity",
    enabled: true,
    config: { fetch_k: 500 },
    next: ["rerank"],
    on_empty: null,
    on_unavailable: null,
    on_timeout: null,
    on_error: null,
  },
  {
    id: "rerank",
    strategy: "rerank.cross_encoder",
    enabled: true,
    config: { top_k: 24 },
    next: [],
    on_empty: null,
    on_unavailable: "retrieve",
    on_timeout: "retrieve",
    on_error: "retrieve",
  },
];

const strategies: PipelineStrategy[] = [
  {
    strategy_id: "retrieve.chroma_similarity",
    version: 1,
    family: "candidate_generation",
    label: "Chroma semantic similarity",
    description: "Embed the query and retrieve nearest candidates from a compatible collection.",
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
    strategy_id: "rerank.cross_encoder",
    version: 1,
    family: "rerank",
    label: "Cross-encoder reranker",
    description: "Score bounded query/candidate pairs with the registered cross-encoder.",
    input_type: "candidate_set",
    output_type: "candidate_set",
    deterministic: false,
    invokes_llm: false,
    capabilities: ["cross_encoder"],
    config_schema: {
      type: "object",
      properties: {
        top_k: { type: "integer", minimum: 1, maximum: 500 },
      },
    },
  },
];

const meta = {
  title: "Pipelines/Stage Editor",
  component: PipelineStageEditor,
  args: {
    stage: stages[0],
    stageIndex: 0,
    stages,
    strategies,
    entryStageIds: ["retrieve"],
  },
} satisfies Meta<typeof PipelineStageEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

export const RetrievalStage: Story = {};

export const CrossEncoderWithFallbacks: Story = {
  args: {
    stage: stages[1],
    stageIndex: 1,
    entryStageIds: ["retrieve"],
  },
};

const structuredMetadata: PipelineStrategy = {
  strategy_id: "llm.structured_metadata",
  version: 1,
  family: "llm",
  label: "Structured metadata generation",
  description: "Run one schema-derived structured metadata task.",
  input_type: "context_packet",
  output_type: "model_output",
  deterministic: false,
  invokes_llm: true,
  capabilities: ["chat_model", "structured_output"],
  config_schema: {
    type: "object",
    properties: {
      provider_role: { type: "string", enum: ["primary", "review"], default: "primary" },
      attempts: { type: "integer", minimum: 1, maximum: 4, default: 2 },
    },
  },
};

const enrichmentStages: PipelineStage[] = [
  {
    id: "primary",
    strategy: "llm.structured_metadata",
    enabled: true,
    config: { provider_role: "primary", attempts: 2 },
    next: [],
    on_empty: null,
    on_unavailable: null,
    on_timeout: "review",
    on_error: "review",
  },
  {
    id: "review",
    strategy: "llm.structured_metadata",
    enabled: true,
    config: { provider_role: "review", attempts: 2 },
    next: [],
  },
];

export const StructuredMetadataWithEscalation: Story = {
  args: {
    stage: enrichmentStages[0],
    stageIndex: 0,
    stages: enrichmentStages,
    strategies: [structuredMetadata],
    entryStageIds: ["primary"],
  },
};
