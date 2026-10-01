/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineRunTracePanel from "./PipelineRunTracePanel.vue";
import type { PipelineRunTrace } from "../../types/pipelines";

const trace: PipelineRunTrace = {
  run_id: "rag-20260928-example",
  feature: "research",
  pipeline_id: "research.balanced",
  pipeline_version: 1,
  resolved_pipeline: {},
  resolved_hash: "abcdef0123456789",
  owner: "researcher",
  status: "completed",
  started_at: "2026-09-28T18:00:00-07:00",
  finished_at: "2026-09-28T18:00:04-07:00",
  total_elapsed_ms: 4120,
  warnings: ["Cross-encoder unavailable; lexical fallback was used."],
  stages: [
    {
      stage_id: "query",
      strategy_id: "query.research_decompose",
      strategy_version: 1,
      status: "completed",
      elapsed_ms: 420,
      input_count: 1,
      output_count: 1,
      parameters: {},
      provider: "ollama",
      model: "qwen3",
    },
    {
      stage_id: "dense",
      strategy_id: "retrieve.chroma_similarity",
      strategy_version: 1,
      status: "completed",
      input_count: 1,
      output_count: 64,
      parameters: { fetch_k: 500 },
      collection: "derrida_primary",
      score_summary: { distance_metric_normalized: true },
    },
    {
      stage_id: "rerank",
      strategy_id: "rerank.cross_encoder",
      strategy_version: 1,
      status: "unavailable",
      elapsed_ms: 180,
      input_count: 64,
      output_count: 24,
      parameters: {},
      provider: "sentence-transformers",
      model: "cross-encoder/ms-marco-MiniLM-L-6-v2",
      fallback_reason: "Model could not be loaded; lexical/vector fallback ran.",
    },
    {
      stage_id: "fallback",
      strategy_id: "rerank.lexical_fallback",
      strategy_version: 1,
      status: "completed",
      elapsed_ms: 30,
      input_count: 64,
      output_count: 24,
      parameters: {},
    },
    {
      stage_id: "generate",
      strategy_id: "llm.generate_answer",
      strategy_version: 1,
      status: "completed",
      elapsed_ms: 2850,
      input_count: 12,
      output_count: 1,
      parameters: {},
      provider: "ollama",
      model: "qwen3",
    },
  ],
};

const meta = {
  title: "Pipelines/Run Trace",
  component: PipelineRunTracePanel,
  args: { trace },
} satisfies Meta<typeof PipelineRunTracePanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithFallback: Story = {};

export const CompactMobile: Story = {
  parameters: {
    viewport: { defaultViewport: "mobile1" },
  },
};

export const RewiredInputs: Story = {
  args: {
    trace: { ...trace, warnings: ["rewired_inputs: provenance.candidates, select.candidates"] },
  },
};
