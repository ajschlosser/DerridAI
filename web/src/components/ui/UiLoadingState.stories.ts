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

export const Inline: Story = { args: { label: "Updating…", detail: "", variant: "inline" } };
export const InlineFrench: Story = {
  args: {
    label: "Mise à jour…",
    detail: "Le contenu reste disponible pendant la mise à jour.",
    variant: "inline",
  },
};
