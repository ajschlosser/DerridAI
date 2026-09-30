/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineEditorVersionDetails from "./PipelineEditorVersionDetails.vue";
import type { PipelineDefinition } from "../../types/pipelines";

const draft: PipelineDefinition = {
  pipeline_id: "reviewer_evidence",
  version: 8,
  name: "Reviewer Evidence Recovery",
  purpose: "evidence_suggestion",
  status: "draft",
  entry_stage_ids: ["query"],
  stages: [],
  notes: null,
};

const meta = {
  title: "Pipelines/Editor Version Details",
  component: PipelineEditorVersionDetails,
  args: { modelValue: draft },
} satisfies Meta<typeof PipelineEditorVersionDetails>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Collapsed: Story = {};

export const OpenWhenIdentityIncomplete: Story = {
  args: { modelValue: { ...draft, name: "" } },
};
