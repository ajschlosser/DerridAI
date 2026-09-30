/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import PipelineStrategiesWorkspace from "./PipelineStrategiesWorkspace.vue";
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
  title: "Pipelines/Strategies Workspace",
  component: PipelineStrategiesWorkspace,
  args: {
    strategies: contractStrategies,
    pipelines,
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    selectedStrategyId: "rerank.cross_encoder",
    filters: {
      query: "",
      family: "",
      computation: "",
      capability: "",
      effect: "",
      workflow: "",
    },
  },
  render: (args) => ({
    components: { PipelineStrategiesWorkspace },
    setup() {
      const filters = ref({ ...args.filters });
      const selected = ref(args.selectedStrategyId);
      return { args, filters, selected };
    },
    template:
      '<PipelineStrategiesWorkspace v-bind="args" v-model:filters="filters" :selected-strategy-id="selected" @select-strategy="selected = $event" />',
  }),
} satisfies Meta<typeof PipelineStrategiesWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AllStrategies: Story = {};

export const French: Story = { parameters: { locale: "fr-CA" } };

export const FilteredByEffect: Story = {
  args: {
    filters: {
      query: "",
      family: "",
      computation: "deterministic",
      capability: "",
      effect: "provenance_gate",
      workflow: "",
    },
  },
};

export const Empty: Story = { args: { strategies: [] } };
