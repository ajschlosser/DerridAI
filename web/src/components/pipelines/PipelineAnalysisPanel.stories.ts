/* Copyright 2026 Aaron John Schlosser, PhD. */
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
