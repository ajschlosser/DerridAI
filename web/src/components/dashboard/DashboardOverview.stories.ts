/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import DashboardOverview from "./DashboardOverview.vue";
const meta = {
  title: "Dashboard/Overview",
  component: DashboardOverview,
  args: { totals: { works: 5, records: 124, dbs: 2, changes: 8 } },
} satisfies Meta<typeof DashboardOverview>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
