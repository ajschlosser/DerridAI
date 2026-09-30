/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineExecutionList from "./PipelineExecutionList.vue";
import type { PipelineRunTrace } from "../../types/pipelines";
import { contractPurposes, contractVocabulary } from "./fixtures/pipelineCatalogContract";

const run = (id: string, status: string, feature: string): PipelineRunTrace => ({
  run_id: id,
  feature,
  pipeline_id: "research.current",
  pipeline_version: 7,
  resolved_pipeline: {},
  resolved_hash: "abc",
  status,
  started_at: "2026-09-30T08:31:00Z",
  total_elapsed_ms: 1730,
  stages: [],
});

const meta = {
  title: "Pipelines/Execution List",
  component: PipelineExecutionList,
  args: {
    runs: [
      run("rag-1", "completed", "research"),
      run("rag-2", "failed", "evidence_suggestion.reviewer"),
      run("rag-3", "running", "research"),
    ],
    pipelines: [],
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    selectedRunId: "rag-2",
    total: 3,
    limit: 25,
    offset: 0,
  },
} satisfies Meta<typeof PipelineExecutionList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
