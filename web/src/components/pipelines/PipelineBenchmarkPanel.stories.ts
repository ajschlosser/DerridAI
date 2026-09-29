/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineBenchmarkPanel from "./PipelineBenchmarkPanel.vue";
import type { PipelineDefinition } from "../../types/pipelines";

const pipelines: PipelineDefinition[] = [
  {
    pipeline_id: "research.current",
    version: 1,
    name: "Research — current",
    purpose: "research",
    status: "active",
    entry_stage_ids: ["query"],
    stages: [
      {
        id: "query",
        strategy: "query.research_decompose",
        enabled: true,
        config: {},
        next: ["dense"],
      },
      {
        id: "dense",
        strategy: "retrieve.chroma_similarity",
        enabled: true,
        config: {},
        next: ["pack"],
      },
      {
        id: "pack",
        strategy: "pack.evidence_context",
        enabled: true,
        config: {},
        next: [],
      },
    ],
    runtime_support: { supported: true, adapter: "research" },
  },
  {
    pipeline_id: "research.balanced",
    version: 1,
    name: "Research — balanced",
    purpose: "research",
    status: "draft",
    entry_stage_ids: ["query"],
    stages: [
      {
        id: "query",
        strategy: "query.research_decompose",
        enabled: true,
        config: {},
        next: ["dense"],
      },
      {
        id: "dense",
        strategy: "retrieve.chroma_similarity",
        enabled: true,
        config: {},
        next: ["pack"],
      },
      {
        id: "pack",
        strategy: "pack.evidence_context",
        enabled: true,
        config: {},
        next: [],
      },
    ],
    runtime_support: { supported: true, adapter: "research" },
  },
];

const meta = {
  title: "Pipelines/PipelineBenchmarkPanel",
  component: PipelineBenchmarkPanel,
  args: { pipelines },
} satisfies Meta<typeof PipelineBenchmarkPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
