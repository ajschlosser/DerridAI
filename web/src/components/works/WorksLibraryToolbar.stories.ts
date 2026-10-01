/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import WorksLibraryToolbar from "./WorksLibraryToolbar.vue";

const meta = {
  title: "Works/Library Toolbar",
  component: WorksLibraryToolbar,
  args: {
    mode: "admin",
    query: "",
    sort: "title-asc",
    filters: { needsReview: false, dbStatus: "", author: "" },
    viewMode: "cards",
    authors: ["Jacques Derrida", "Emmanuel Levinas"],
    totalWorks: 64,
    visibleWorks: 64,
    totalReview: 7,
  },
} satisfies Meta<typeof WorksLibraryToolbar>;
export default meta;
type Story = StoryObj<typeof WorksLibraryToolbar>;
export const Default: Story = {};
export const Filtered: Story = {
  args: {
    query: "gla",
    visibleWorks: 1,
    filters: { needsReview: true, dbStatus: "changed", author: "" },
    viewMode: "list",
  },
};
export const Researcher: Story = { args: { mode: "researcher", totalReview: 0 } };
