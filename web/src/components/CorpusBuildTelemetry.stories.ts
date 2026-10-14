/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
