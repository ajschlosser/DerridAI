/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { PipelineDefinition } from "../../types/pipelines";
import PipelineBenchmarkPanel from "./PipelineBenchmarkPanel.vue";

const pipelines: PipelineDefinition[] = [
  {
    pipeline_id: "research.current",
    version: 1,
    name: "Research — current production chain",
    purpose: "research",
    status: "active",
    entry_stage_ids: ["query"],
    stages: [],
    built_in: true,
    runtime_support: { supported: true, adapter: "research" },
  },
  {
    pipeline_id: "research.balanced",
    version: 1,
    name: "Research — balanced",
    purpose: "research",
    status: "draft",
    entry_stage_ids: ["query"],
    stages: [],
    built_in: true,
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
