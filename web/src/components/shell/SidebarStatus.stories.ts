/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SidebarStatus from "./SidebarStatus.vue";

const meta = {
  title: "Shell/Sidebar Status",
  component: SidebarStatus,
  render: (args) => ({
    components: { SidebarStatus },
    setup: () => ({ args }),
    template:
      '<div style="width:220px;background:var(--card);padding:8px"><SidebarStatus v-bind="args" /></div>',
  }),
  args: {
    isAdmin: true,
    hasCorpusDb: true,
    totalLoaded: 4820,
    corpusStoreCount: 3,
    activeStore: "",
    dbRecords: 0,
    selectedEvidenceCount: 0,
  },
} satisfies Meta<typeof SidebarStatus>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Admin: Story = {};
export const Researcher: Story = {
  args: {
    isAdmin: false,
    activeStore: "Derrida — Of Grammatology",
    dbRecords: 1204,
    selectedEvidenceCount: 6,
  },
};
