/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineStrategyCatalog from "./PipelineStrategyCatalog.vue";
import type { PipelineDefinition } from "../../types/pipelines";
import {
  contractPurposes,
  contractStrategies,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";

const stage = (id: string, strategy: string) => ({
  id,
  strategy,
  enabled: true,
  config: {},
  next: [],
});

const pipelines: PipelineDefinition[] = [
  {
    pipeline_id: "research.current",
    version: 1,
    name: "Research — current production chain",
    purpose: "research",
    status: "active",
    entry_stage_ids: ["dense"],
    stages: [stage("dense", "retrieve.chroma_similarity"), stage("rerank", "rerank.cross_encoder")],
    built_in: true,
  },
  {
    pipeline_id: "evidence.reviewer.current",
    version: 2,
    name: "Evidence suggestion — reviewer support-gated",
    purpose: "evidence_suggestion",
    status: "active",
    entry_stage_ids: ["semantic"],
    stages: [
      stage("semantic", "retrieve.source_cosine"),
      stage("rerank", "rerank.cross_encoder"),
      stage("support", "validate.evidence_support"),
    ],
    built_in: true,
  },
];

const meta = {
  title: "Pipelines/Strategy Catalog",
  component: PipelineStrategyCatalog,
  args: {
    strategies: contractStrategies,
    pipelines,
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    selectedStrategyId: "rerank.cross_encoder",
  },
} satisfies Meta<typeof PipelineStrategyCatalog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AllStrategies: Story = {};

export const French: Story = { parameters: { locale: "fr-CA" } };

export const Empty: Story = { args: { strategies: [] } };
