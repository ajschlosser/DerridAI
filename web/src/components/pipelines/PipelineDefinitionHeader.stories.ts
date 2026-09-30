/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineDefinitionHeader from "./PipelineDefinitionHeader.vue";
import type { PipelineDefinition } from "../../types/pipelines";
import {
  contractPurpose,
  contractPurposes,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";

const pipeline: PipelineDefinition = {
  pipeline_id: "research.current",
  version: 7,
  name: "Hybrid Research",
  purpose: "research",
  status: "active",
  entry_stage_ids: ["retrieve"],
  stages: [],
  built_in: true,
  validation: { valid: true, issues: [] },
  runtime_support: { supported: true, adapter: "research" },
};

const meta = {
  title: "Pipelines/Definition Header",
  component: PipelineDefinitionHeader,
  args: {
    pipeline,
    purpose: contractPurpose("research"),
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    assignment: null,
    assigned: true,
    canAssign: true,
    assigning: false,
    cloning: false,
  },
} satisfies Meta<typeof PipelineDefinitionHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ActiveAssignment: Story = {};

export const DraftInspectOnly: Story = {
  args: {
    pipeline: {
      ...pipeline,
      version: 8,
      status: "draft",
      runtime_support: { supported: false, reason: "The adapter cannot run this graph shape." },
    },
    assigned: false,
    canAssign: false,
  },
};

export const InvalidWithCustomAssignment: Story = {
  args: {
    pipeline: { ...pipeline, validation: { valid: false, issues: [] } },
    assigned: false,
    assignment: {
      feature: "research",
      pipeline_id: "research.custom",
      pipeline_version: 2,
      scope: "system",
      override_allowed: true,
      source: "system",
    },
  },
};
