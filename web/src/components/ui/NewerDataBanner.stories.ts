/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import NewerDataBanner from "./NewerDataBanner.vue";

const meta = {
  title: "UI/NewerDataBanner",
  component: NewerDataBanner,
  parameters: { layout: "padded" },
  args: { visible: true },
} satisfies Meta<typeof NewerDataBanner>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Visible: Story = {};
export const Hidden: Story = { args: { visible: false } };
