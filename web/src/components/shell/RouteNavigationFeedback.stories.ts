/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RouteNavigationFeedback from "./RouteNavigationFeedback.vue";
const meta = {
  title: "Shell/RouteNavigationFeedback",
  component: RouteNavigationFeedback,
  args: { destination: "Works", failed: false },
} satisfies Meta<typeof RouteNavigationFeedback>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Loading: Story = {};
export const Failed: Story = { args: { failed: true } };
export const LongDestination: Story = {
  args: { destination: "Relations entre les notices et les sources documentaires", failed: true },
};
