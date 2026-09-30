/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineStrategyInspector from "./PipelineStrategyInspector.vue";
import type { PipelineDefinition } from "../../types/pipelines";
import {
  contractPurposes,
  contractStrategy,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";

const pipeline: PipelineDefinition = {
  pipeline_id: "research.current",
  version: 1,
  name: "Research — current production chain",
  purpose: "research",
  status: "active",
  entry_stage_ids: ["rerank"],
  stages: [
    {
      id: "rerank",
      strategy: "rerank.cross_encoder",
      enabled: true,
      config: {},
      next: [],
    },
  ],
};

const meta = {
  title: "Pipelines/Strategy Inspector",
  component: PipelineStrategyInspector,
  args: {
    strategy: contractStrategy("rerank.cross_encoder"),
    usage: { pipelines: [pipeline], categories: ["research"] },
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
  },
} satisfies Meta<typeof PipelineStrategyInspector>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Used: Story = {};

export const Unused: Story = { args: { usage: { pipelines: [], categories: [] } } };
