/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineDefinitionDetail from "./PipelineDefinitionDetail.vue";
import type {
  PipelineAssignment,
  PipelineDefinition,
  PipelineStrategy,
} from "../../types/pipelines";

const strategies: PipelineStrategy[] = [
  {
    strategy_id: "retrieve.chroma_similarity",
    version: 1,
    family: "candidate_generation",
    label: "Chroma semantic similarity",
    description: "Retrieve semantic candidates from a compatible collection.",
    input_type: "query",
    output_type: "candidate_set",
    deterministic: false,
    invokes_llm: false,
    capabilities: ["embedding", "chroma"],
    config_schema: { type: "object", properties: {} },
  },
  {
    strategy_id: "validate.provenance",
    version: 1,
    family: "support_validation",
    label: "Provenance sufficiency gate",
    description: "Require source identity and citation bindings.",
    input_type: "candidate_set",
    output_type: "candidate_set",
    deterministic: true,
    invokes_llm: false,
    capabilities: [],
    config_schema: { type: "object", properties: {} },
  },
];

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
