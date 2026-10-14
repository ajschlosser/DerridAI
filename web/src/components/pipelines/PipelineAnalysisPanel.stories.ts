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
import PipelineAnalysisPanel from "./PipelineAnalysisPanel.vue";
import { analysisFixture } from "./fixtures/pipelineAnalysisFixture";
import { contractStrategies, contractVocabulary } from "./fixtures/pipelineCatalogContract";

const meta = {
  title: "Pipelines/Analysis Panel",
  component: PipelineAnalysisPanel,
  args: {
    analysis: analysisFixture(),
    strategies: contractStrategies,
    vocabulary: contractVocabulary,
    selectedStageId: "a",
  },
  decorators: [() => ({ template: '<div style="max-width: 860px"><story /></div>' })],
} satisfies Meta<typeof PipelineAnalysisPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const PartlyMeasured: Story = {};

export const NeverRun: Story = {
  args: {
    analysis: (() => {
      const value = analysisFixture();
      value.latency.observed_runs = { samples: 0 };
      value.sample = { runs: 0, pipeline_runs: 0, exact_runs: 0 };
      value.latency.stages = value.latency.stages.map((row) => ({
        ...row,
        basis: "none" as const,
        samples: 0,
        p50_ms: null,
        p90_ms: null,
      }));
      value.latency.typical_ms = 0;
      value.latency.slow_ms = 0;
      return value;
    })(),
  },
};

export const Loading: Story = { args: { analysis: null, loading: true } };

export const Failed: Story = { args: { error: "Request failed (500)" } };

export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
