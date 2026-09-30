/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineDefinitionDetail from "./PipelineDefinitionDetail.vue";
import type {
  PipelineAssignment,
  PipelineDefinition,
  PipelineStrategy,
} from "../../types/pipelines";
import {
  contractPurpose,
  contractPurposes,
  contractStrategy,
  contractVocabulary,
} from "./fixtures/pipelineCatalogContract";

const strategies: PipelineStrategy[] = ["retrieve.chroma_similarity", "validate.provenance"].map(
  contractStrategy,
);

const pipeline: PipelineDefinition = {
  pipeline_id: "research.current",
  version: 1,
  name: "Research — current production chain",
  purpose: "research",
  status: "active",
  entry_stage_ids: ["retrieve"],
  built_in: true,
  stages: [
    {
      id: "retrieve",
      strategy: "retrieve.chroma_similarity",
      enabled: true,
      config: {},
      next: ["provenance"],
    },
    {
      id: "provenance",
      strategy: "validate.provenance",
      enabled: true,
      config: {},
      next: [],
    },
  ],
  validation: {
    valid: true,
    issues: [
      {
        level: "warning",
        code: "example",
        message: "Example warning shown for visual coverage.",
      },
    ],
  },
  runtime_support: { supported: true, adapter: "research" },
};

const assignment: PipelineAssignment = {
  feature: "research",
  pipeline_id: "research.current",
  pipeline_version: 1,
  scope: "system",
  scope_id: null,
  override_allowed: true,
  source: "built_in",
};

const meta = {
  title: "Pipelines/Definition Detail",
  component: PipelineDefinitionDetail,
  args: {
    pipeline,
    strategies,
    purpose: contractPurpose("research"),
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    assignment,
    assigned: true,
    canAssign: true,
    assigning: false,
    cloning: false,
  },
} satisfies Meta<typeof PipelineDefinitionDetail>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Assigned: Story = {};

export const InspectOnly: Story = {
  args: {
    assigned: false,
    canAssign: false,
    pipeline: {
      ...pipeline,
      status: "draft",
      runtime_support: {
        supported: false,
        adapter: null,
        reason: "This graph is inspectable but not executable by the current adapter.",
      },
    },
  },
};

export const FrenchContract: Story = {
  parameters: { locale: "fr-CA" },
};

export const UnregisteredPurpose: Story = {
  args: {
    purpose: null,
    assigned: false,
    canAssign: false,
    pipeline: { ...pipeline, purpose: "legacy_experiment", status: "draft" },
  },
};
