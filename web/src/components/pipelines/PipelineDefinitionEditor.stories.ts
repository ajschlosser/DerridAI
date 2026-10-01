/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import PipelineDefinitionEditor from "./PipelineDefinitionEditor.vue";
import type { PipelineDefinition, PipelineStrategy } from "../../types/pipelines";
import { analysisFixture } from "./fixtures/pipelineAnalysisFixture";
import {
  contractPurpose,
  contractStrategy,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";

const strategies: PipelineStrategy[] = [
  "retrieve.chroma_similarity",
  "select.source_diversity",
].map(contractStrategy);

const pipeline: PipelineDefinition = {
  pipeline_id: "research.custom",
  version: 3,
  name: "Research — source-diverse",
  purpose: "research",
  status: "draft",
  entry_stage_ids: ["dense"],
  stages: [
    {
      id: "dense",
      strategy: "retrieve.chroma_similarity",
      enabled: true,
      config: { fetch_k: 500 },
      next: ["diversity"],
    },
    {
      id: "diversity",
      strategy: "select.source_diversity",
      enabled: true,
      config: { limit: 24 },
      next: [],
    },
  ],
  built_in: false,
  notes: "Tune on the fixed DerridAI retrieval benchmark before activation.",
};

const meta = {
  title: "Pipelines/Definition Editor",
  component: PipelineDefinitionEditor,
  args: {
    modelValue: pipeline,
    strategies,
  },
  render: (args) => ({
    components: { PipelineDefinitionEditor },
    setup() {
      const value = ref(structuredClone(args.modelValue));
      return { args, value };
    },
    template:
      '<PipelineDefinitionEditor v-model="value" :strategies="args.strategies" style="max-width: 1180px" />',
  }),
} satisfies Meta<typeof PipelineDefinitionEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

export const DraftVersion: Story = {};

const analyzed: PipelineDefinition = {
  ...pipeline,
  entry_stage_ids: ["a"],
  stages: [
    { id: "a", strategy: "retrieve.chroma_similarity", enabled: true, config: {}, next: ["b"] },
    { id: "b", strategy: "validate.provenance", enabled: true, config: {}, next: ["c"] },
    { id: "c", strategy: "pack.evidence_context", enabled: true, config: {}, next: [] },
  ],
};

// With the server's analysis the editor shows each stage's inputs and outputs,
// the diagram lenses, and the latency and complexity panel.
export const WithAnalysis: Story = {
  args: {
    modelValue: analyzed,
    strategies: [
      "retrieve.chroma_similarity",
      "validate.provenance",
      "pack.evidence_context",
      "rerank.cross_encoder",
    ].map(contractStrategy),
    purpose: contractPurpose("research"),
    vocabulary: contractVocabulary,
    analysis: analysisFixture(),
  },
  render: (args) => ({
    components: { PipelineDefinitionEditor },
    setup() {
      const value = ref(JSON.parse(JSON.stringify(args.modelValue)));
      return { args, value };
    },
    template:
      '<PipelineDefinitionEditor v-model="value" :strategies="args.strategies" :purpose="args.purpose" :vocabulary="args.vocabulary" :analysis="args.analysis" style="max-width: 1180px" />',
  }),
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
