import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuildTelemetry from "./CorpusBuildTelemetry.vue";

const meta = {
  title: "Corpus Builder/Build/Telemetry",
  component: CorpusBuildTelemetry,
  args: {
    stage: "enriching",
    validation: null,
    llmMetrics: { calls: 81, retries: 3, structured_output_failures: 3, escalations: 0 },
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
} satisfies Meta<typeof CorpusBuildTelemetry>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Running: Story = {};
export const ProvenanceHazard: Story = {
  args: {
    stage: "review",
    unresolvedCount: 1,
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
export const ValidationAttention: Story = {
  args: {
    stage: "review",
    validation: {
      valid: false,
      coverage: 0.98,
      metadata_evidence_errors: [{ field: "position_holder" }],
    },
  },
};
