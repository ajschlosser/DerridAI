/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { h } from "vue";
import PipelineTypeChip from "./PipelineTypeChip.vue";

const meta = {
  title: "Pipelines/Data Type Chip",
  component: PipelineTypeChip,
  args: { type: "candidate_set" },
} satisfies Meta<typeof PipelineTypeChip>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Single: Story = {};

// Each type has its own glyph and edge colour, so none relies on colour alone.
export const AllTypes: Story = {
  render: () => ({
    render: () =>
      h(
        "div",
        { style: "display:flex;flex-wrap:wrap;gap:8px" },
        ["query", "candidate_set", "context_packet", "model_output", "evaluation", "any"].map(
          (type) => h(PipelineTypeChip, { type }),
        ),
      ),
  }),
};
