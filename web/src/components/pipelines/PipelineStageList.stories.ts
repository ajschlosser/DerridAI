/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineStageList from "./PipelineStageList.vue";
import type { PipelineDefinition, PipelineStrategy } from "../../types/pipelines";
import { contractStrategy } from "./fixtures/pipelineCatalogContract";

const strategies: PipelineStrategy[] = [
  "retrieve.chroma_similarity",
  "rerank.cross_encoder",
  "llm.generate_answer",
].map(contractStrategy);

const pipeline: PipelineDefinition = {
  pipeline_id: "research.example",
  version: 2,
  name: "Research example",
  purpose: "research",
  status: "active",
  entry_stage_ids: ["dense"],
  stages: [
    {
      id: "dense",
      strategy: "retrieve.chroma_similarity",
      enabled: true,
      config: { fetch_k: 500 },
      next: ["rerank"],
    },
    {
      id: "rerank",
      strategy: "rerank.cross_encoder",
      enabled: true,
      config: {},
      next: ["generate"],
      on_unavailable: "generate",
    },
    {
      id: "generate",
      strategy: "llm.generate_answer",
      enabled: true,
      config: {},
      next: [],
    },
  ],
};

const meta = {
  title: "Pipelines/Stage List",
  component: PipelineStageList,
  args: { pipeline, strategies },
} satisfies Meta<typeof PipelineStageList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
