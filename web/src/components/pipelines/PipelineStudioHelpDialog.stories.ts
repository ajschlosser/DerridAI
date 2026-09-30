/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PipelineStudioHelpDialog from "./PipelineStudioHelpDialog.vue";

const meta = {
  title: "Pipelines/Studio Help Dialog",
  component: PipelineStudioHelpDialog,
  args: { open: true },
} satisfies Meta<typeof PipelineStudioHelpDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Open: Story = {};

export const French: Story = { parameters: { locale: "fr-CA" } };
