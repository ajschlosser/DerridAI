/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineExecutionsWorkspace from "./PipelineExecutionsWorkspace.vue";
import type { PipelineRunTrace } from "../../types/pipelines";
import {
  contractPurposes,
  contractStrategies,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";

const runs: PipelineRunTrace[] = [
  {
    run_id: "rag-20260929-001",
    feature: "research",
    pipeline_id: "research.current",
    pipeline_version: 1,
    resolved_pipeline: {},
    resolved_hash: "abc",
    status: "completed",
    started_at: "2026-09-29T02:00:00Z",
    finished_at: "2026-09-29T02:00:04Z",
    total_elapsed_ms: 4000,
    warnings: [],
    stages: [
      {
        stage_id: "retrieve",
        strategy_id: "retrieve.chroma_similarity",
        strategy_version: 1,
        status: "completed",
        elapsed_ms: 150,
        input_count: 1,
        output_count: 64,
        parameters: {},
        collection: "derrida_primary",
      },
    ],
  },
  {
    run_id: "rag-20260929-002",
    feature: "research",
    pipeline_id: "research.custom",
    pipeline_version: 2,
    resolved_pipeline: {},
    resolved_hash: "def",
    status: "failed",
    started_at: "2026-09-29T01:30:00Z",
    finished_at: "2026-09-29T01:30:01Z",
    total_elapsed_ms: 1000,
    warnings: ["Provider was unavailable."],
    stages: [],
  },
];

const meta = {
  title: "Pipelines/Executions Workspace",
  component: PipelineExecutionsWorkspace,
  args: {
    runs,
    pipelines: [],
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    strategies: contractStrategies,
    selectedRunId: runs[0].run_id,
    focusedRun: null,
    filters: { query: "", category: "", feature: "", pipelineId: "", status: "", owner: "" },
    total: runs.length,
    limit: 25,
    offset: 0,
  },
} satisfies Meta<typeof PipelineExecutionsWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const FailedRunSelected: Story = {
  args: { selectedRunId: runs[1].run_id },
};

export const Empty: Story = {
  args: { runs: [], selectedRunId: "" },
};
