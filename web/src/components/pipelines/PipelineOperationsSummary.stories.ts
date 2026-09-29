/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineOperationsSummary from "./PipelineOperationsSummary.vue";
import type { PipelineOperationalMetrics } from "../../types/pipelines";

const metrics: PipelineOperationalMetrics = {
  sampled_run_count: 128,
  status_counts: { completed: 123, failed: 5 },
  fallback_run_count: 17,
  warning_run_count: 21,
  average_run_elapsed_ms: 1320,
  p95_run_elapsed_ms: 3180,
  features: [
    {
      feature: "research",
      run_count: 72,
      failed_count: 2,
      fallback_run_count: 9,
      warning_run_count: 11,
      average_elapsed_ms: 1680,
      p95_elapsed_ms: 3420,
    },
    {
      feature: "metadata_precedents",
      run_count: 41,
      failed_count: 2,
      fallback_run_count: 6,
      warning_run_count: 8,
      average_elapsed_ms: 910,
      p95_elapsed_ms: 1820,
    },
    {
      feature: "evidence_suggestion.reviewer",
      run_count: 15,
      failed_count: 1,
      fallback_run_count: 2,
      warning_run_count: 2,
      average_elapsed_ms: 510,
      p95_elapsed_ms: 900,
    },
  ],
  strategies: [
    {
      strategy_id: "rerank.cross_encoder",
      stage_ids: ["rerank"],
      executions: 97,
      fallback_count: 11,
      warning_count: 11,
      model_call_count: 86,
      issue_count: 11,
      status_counts: { completed: 86, unavailable: 8, timed_out: 3 },
      average_elapsed_ms: 410,
      p95_elapsed_ms: 980,
      average_input_count: 24,
      average_output_count: 18,
    },
    {
      strategy_id: "retrieve.chroma_similarity",
      stage_ids: ["dense", "retrieve"],
      executions: 113,
      fallback_count: 4,
      warning_count: 5,
      model_call_count: 0,
      issue_count: 4,
      status_counts: { completed: 109, unavailable: 4 },
      average_elapsed_ms: 125,
      p95_elapsed_ms: 260,
      average_input_count: 1,
      average_output_count: 42,
    },
    {
      strategy_id: "validate.provenance",
      stage_ids: ["provenance"],
      executions: 87,
      fallback_count: 0,
      warning_count: 0,
      model_call_count: 0,
      issue_count: 0,
      status_counts: { completed: 87 },
      average_elapsed_ms: 12,
      p95_elapsed_ms: 20,
      average_input_count: 18,
      average_output_count: 17,
    },
  ],
  sample_limit: 250,
  feature_filter: null,
  owner_filter: null,
};

const meta = {
  title: "Pipelines/Operational Health",
  component: PipelineOperationsSummary,
  args: {
    metrics,
  },
} satisfies Meta<typeof PipelineOperationsSummary>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Populated: Story = {};

export const Empty: Story = {
  args: {
    metrics: {
      sampled_run_count: 0,
      status_counts: {},
      fallback_run_count: 0,
      warning_run_count: 0,
      average_run_elapsed_ms: null,
      p95_run_elapsed_ms: null,
      features: [],
      strategies: [],
      sample_limit: 250,
      feature_filter: null,
      owner_filter: null,
    },
  },
};
