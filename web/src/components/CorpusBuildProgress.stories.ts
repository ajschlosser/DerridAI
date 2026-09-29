import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuildProgress from "./CorpusBuildProgress.vue";

const meta = {
  title: "Corpus Builder/Workflow/Build Progress",
  component: CorpusBuildProgress,
  args: {
    status: "running",
    stage: "enriching",
    progress: 0.63,
    recordCount: 187,
    reviewCount: 12,
    acceptedCount: 0,
    warnings: [],
    validation: null,
    llmMetrics: { calls: 81, retries: 3, structured_output_failures: 3, escalations: 0 },
    metadataActiveTasks: [{ record_id: "record-0036", task: "quotation" }],
    metadataTasksTotal: 561,
    metadataTasksCompleted: 214,
    metadataTasksFailed: 2,
    metadataTasksSkipped: 7,
    metadataTasksRunning: 3,
    metadataTasksQueued: 335,
    segmentationTelemetry: {
      candidateCount: 54,
      deterministicSplits: 5,
      deterministicKeeps: 31,
      llmAdjudications: 12,
      llmBatchCalls: 2,
      llmSplits: 4,
      llmKeeps: 8,
      provisionalSplits: 1,
      budgetSkipped: 6,
      classifierFailures: 0,
      reviewCount: 0,
    },
  },
} satisfies Meta<typeof CorpusBuildProgress>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Running: Story = {};
export const SegmentingCandidates: Story = {
  args: {
    status: "running",
    stage: "segmenting",
    progress: 0.27,
    recordCount: 0,
    reviewCount: 0,
    acceptedCount: 0,
    boundaryCandidatesCompleted: 42,
    segmentationTelemetry: {
      candidateCount: 67,
      deterministicSplits: 8,
      deterministicKeeps: 22,
      llmAdjudications: 12,
      llmBatchCalls: 2,
      llmSplits: 4,
      llmKeeps: 8,
      provisionalSplits: 0,
      budgetSkipped: 0,
      classifierFailures: 0,
      reviewCount: 0,
    },
  },
};
export const NeedsReview: Story = {
  args: {
    status: "awaiting_review",
    stage: "review",
    progress: 1,
    recordCount: 287,
    reviewCount: 17,
    acceptedCount: 270,
    validation: {
      valid: false,
      coverage: 1,
      metadata_evidence_errors: [{ field: "position_holder" }],
    },
    warnings: ["One metadata record requires manual review."],
  },
};
export const RecoverableFailure: Story = {
  args: {
    status: "failed",
    stage: "failed",
    progress: 0.48,
    recordCount: 84,
    reviewCount: 0,
    acceptedCount: 0,
    error: "Provider unavailable. Resume from the last checkpoint after restoring the provider.",
    warnings: ["Completed segmentation and metadata checkpoints were preserved."],
  },
};
export const ProvenanceHazard: Story = {
  args: {
    status: "awaiting_review",
    stage: "review",
    progress: 1,
    recordCount: 31,
    reviewCount: 0,
    acceptedCount: 0,
    unresolvedCount: 1,
    warnings: ["One forced protected-seam safety split requires boundary review."],
    validation: { valid: true, coverage: 1 },
    segmentationTelemetry: {
      candidateCount: 23,
      deterministicSplits: 3,
      deterministicKeeps: 12,
      llmAdjudications: 8,
      llmBatchCalls: 2,
      llmSplits: 2,
      llmKeeps: 6,
      provisionalSplits: 1,
      budgetSkipped: 0,
      classifierFailures: 0,
      reviewCount: 1,
    },
  },
};
