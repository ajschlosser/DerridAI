/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineWorkflowContract from "./PipelineWorkflowContract.vue";
import type { PipelineDefinition } from "../../types/pipelines";
import { contractPurpose, contractVocabulary } from "./fixtures/pipelineCatalogContract";

const pipeline: PipelineDefinition = {
  pipeline_id: "evidence.reviewer.current",
  version: 2,
  name: "Evidence suggestion — reviewer support-gated",
  purpose: "evidence_suggestion",
  status: "active",
  entry_stage_ids: ["query"],
  stages: [],
  built_in: true,
};

const meta = {
  title: "Pipelines/Workflow Contract",
  component: PipelineWorkflowContract,
  args: {
    pipeline,
    purpose: contractPurpose("evidence_suggestion"),
    vocabulary: contractVocabulary,
  },
} satisfies Meta<typeof PipelineWorkflowContract>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ReviewerEvidence: Story = {};

export const Research: Story = {
  args: {
    pipeline: { ...pipeline, pipeline_id: "research.current", version: 1, purpose: "research" },
    purpose: contractPurpose("research"),
  },
};

export const VectorStoreSearch: Story = {
  args: {
    pipeline: {
      ...pipeline,
      pipeline_id: "store_search.similarity",
      version: 1,
      purpose: "vector_store_search",
    },
    purpose: contractPurpose("vector_store_search"),
  },
};

export const French: Story = { parameters: { locale: "fr-CA" } };
