/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import DashboardSearchPanel from "./DashboardSearchPanel.vue";

const meta = {
  title: "Dashboard/Search Panel",
  component: DashboardSearchPanel,
  args: {
    query: "hospitality",
    mode: "traditional",
    works: [{ work: "Of Hospitality", count: 12, year: "1997" }],
  },
} satisfies Meta<typeof DashboardSearchPanel>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
