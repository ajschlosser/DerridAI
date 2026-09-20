/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import DashboardHero from "./DashboardHero.vue";
const meta = { title: "Dashboard/Hero", component: DashboardHero } satisfies Meta<
  typeof DashboardHero
>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
