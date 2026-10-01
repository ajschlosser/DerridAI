/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineStagePalette from "./PipelineStagePalette.vue";
import {
  contractPurpose,
  contractStrategies,
  contractStrategy,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";
import type { PipelineStage } from "../../types/pipelines";

const anchor: PipelineStage = {
  id: "dense",
  strategy: "retrieve.chroma_similarity",
  enabled: true,
  config: {},
  next: ["rrf"],
};

const meta = {
  title: "Pipelines/Stage Palette",
  component: PipelineStagePalette,
  args: {
    strategies: contractStrategies,
    purpose: contractPurpose("research"),
    vocabulary: contractVocabulary,
    anchor,
    anchorStrategy: contractStrategy("retrieve.chroma_similarity"),
    latency: {
      "rerank.cross_encoder": {
        samples: 40,
        p50_ms: 850,
        p90_ms: 1600,
        reliable: true,
        executions: 44,
        median_ms_per_input: 3,
        by_model: [],
        observed_scaling: null,
      },
    },
  },
} satisfies Meta<typeof PipelineStagePalette>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AfterRetrieval: Story = {};

export const StartingPoint: Story = { args: { anchor: null, anchorStrategy: null } };

export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
