/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiLoadingState from "./UiLoadingState.vue";

const meta = {
  title: "UI/UiLoadingState",
  component: UiLoadingState,
  parameters: {
    layout: "centered",
  },
  args: {
    label: "Loading works",
    detail: "Checking the local corpus database.",
  },
} satisfies Meta<typeof UiLoadingState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Status: Story = {};

export const Skeleton: Story = {
  args: {
    label: "Loading 24 work cards",
    variant: "skeleton",
    skeletonCount: 4,
  },
};
