/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineComparisonResult from "./PipelineComparisonResult.vue";
import type {
  ResearchPipelineComparisonResult,
  ResearchPipelineComparisonSide,
} from "../../types/pipelines";

const phase = (ids: string[]) => ({
  count: ids.length,
  record_ids: ids,
  scores: {
    relevance: { count: 0 },
    rrf_score: { count: 0 },
    rerank_score: { count: 0 },
  },
});

function side(name: string, version: number, ids: string[]): ResearchPipelineComparisonSide {
  return {
    pipeline: { pipeline_id: "research", pipeline_version: version, pipeline_hash: name, name },
    elapsed_seconds: 1.2,
    warnings: [],
    retrieval: {},
    candidate_retention: "complete_for_comparison",
    candidates: {
      pre_rerank: phase([...ids, "spare"]),
      post_rerank: phase(ids),
      post_selection: phase(ids),
    },
    context_characters: 840,
    resource_use: { query_transform_model_calls: 0, cross_encoder_calls: 1 },
    stages: [],
    evidence: ids.map((id, index) => ({
      record_id: id,
      rank: index + 1,
      work: "Of Grammatology",
      citation: "Author 1976: 65",
      retrieval_hits: [],
    })),
  };
}

const overlap = {
  shared_record_ids: ["rec_015"],
  left_only_record_ids: ["rec_001"],
  right_only_record_ids: ["rec_112"],
  shared_count: 1,
  union_count: 3,
  jaccard_overlap: 1 / 3,
};

const result: ResearchPipelineComparisonResult = {
  non_persistent: true,
  left: side("Hybrid Research", 7, ["rec_001", "rec_015"]),
  right: side("Hybrid Research", 9, ["rec_112", "rec_015"]),
  comparison: {
    ...overlap,
    candidate_overlap: { ...overlap, jaccard_overlap: 0.61 },
    post_rerank_overlap: overlap,
    rank_changes: [{ record_id: "rec_015", left_rank: 2, right_rank: 2, rank_delta: 0 }],
  },
};

const meta = {
  title: "Pipelines/Comparison Result",
  component: PipelineComparisonResult,
  args: { result },
} satisfies Meta<typeof PipelineComparisonResult>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AdHocComparison: Story = {};

export const BenchmarkWithDriftWarning: Story = {
  args: {
    benchmarkMeta: {
      benchmarkRunId: "benchmark-1",
      caseId: "trace-definition-001",
      caseVersion: 3,
      corpusFingerprint: "a".repeat(64),
      warnings: ["Index was rebuilt after the case was captured."],
    },
  },
};
