/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineStageInspector from "./PipelineStageInspector.vue";
import type { PipelineGraphNode } from "../../domain/pipelineGraph";
import { contractStrategy, contractVocabulary } from "./fixtures/pipelineCatalogContract";

const node: PipelineGraphNode = {
  id: "retrieve_dense",
  strategy: "retrieve.chroma_similarity",
  enabled: true,
  entry: true,
  x: 0,
  y: 0,
  executionStatus: null,
  presence: "configured",
  elapsedMs: null,
  inputCount: null,
  outputCount: null,
  fallbackReason: null,
};

const meta = {
  title: "Pipelines/Stage Inspector",
  component: PipelineStageInspector,
  args: {
    node,
    strategy: contractStrategy("retrieve.chroma_similarity"),
    vocabulary: contractVocabulary,
  },
} satisfies Meta<typeof PipelineStageInspector>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Configured: Story = {};

export const ExecutedWithFallback: Story = {
  args: {
    hasExecution: true,
    node: {
      ...node,
      executionStatus: "unavailable",
      elapsedMs: 1730,
      inputCount: 1,
      outputCount: 0,
      fallbackReason: "Embedding model unavailable; used lexical retrieval.",
    },
  },
};

export const NotReached: Story = {
  args: {
    hasExecution: true,
    node: { ...node, entry: false, executionStatus: "not_reached", presence: "not_reached" },
  },
};
