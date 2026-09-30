/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineStageNavigator from "./PipelineStageNavigator.vue";
import type { PipelineStage } from "../../types/pipelines";
import { contractStrategies } from "./fixtures/pipelineCatalogContract";

const stage = (id: string, strategy: string, enabled = true): PipelineStage => ({
  id,
  strategy,
  enabled,
  config: {},
  next: [],
});

const meta = {
  title: "Pipelines/Stage Navigator",
  component: PipelineStageNavigator,
  args: {
    stages: [
      stage("analyze_query", "query.passthrough"),
      stage("retrieve_dense", "retrieve.chroma_similarity"),
      stage("provenance_gate", "validate.provenance", false),
    ],
    strategies: contractStrategies,
    selectedIndex: 1,
    entryStageIds: ["analyze_query"],
    canAdd: true,
  },
} satisfies Meta<typeof PipelineStageNavigator>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const French: Story = { parameters: { locale: "fr-CA" } };
