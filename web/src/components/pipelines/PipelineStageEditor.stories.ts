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
