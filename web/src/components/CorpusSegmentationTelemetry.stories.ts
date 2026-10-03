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
import CorpusSegmentationTelemetry from "./CorpusSegmentationTelemetry.vue";

const meta = {
  title: "Corpus Builder/Status/Segmentation Telemetry",
  component: CorpusSegmentationTelemetry,
  args: {
    candidateCount: 54,
    deterministicSplits: 5,
    deterministicKeeps: 31,
    llmAdjudications: 12,
    llmBatchCalls: 2,
    llmSplits: 4,
    llmKeeps: 8,
    provisionalSplits: 5,
    sizeOptimizedSplits: 5,
    absoluteSafetySplits: 0,
    budgetSkipped: 6,
    classifierFailures: 0,
    reviewCount: 0,
  },
} satisfies Meta<typeof CorpusSegmentationTelemetry>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Typical: Story = {};
export const RecoverableFailures: Story = {
  args: { classifierFailures: 3, llmSplits: 2, llmKeeps: 10, reviewCount: 0 },
};
export const ProvenanceHazard: Story = { args: { reviewCount: 1, provisionalSplits: 1 } };
