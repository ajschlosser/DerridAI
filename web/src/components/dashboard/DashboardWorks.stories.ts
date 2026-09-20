/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import DashboardWorks from "./DashboardWorks.vue";
const meta = {
  title: "Dashboard/Works",
  component: DashboardWorks,
  args: { works: [{ work: "Of Hospitality", count: 12, year: "1997" }] },
} satisfies Meta<typeof DashboardWorks>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
