/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import SidebarMoreTools from "./SidebarMoreTools.vue";
import type { SidebarNavEntry } from "./sidebarNav";

const items: SidebarNavEntry[] = [
  {id: "list", label: "Records", icon: "list", active: false},
  {id: "pdf", label: "Corpus Builder", icon: "pdf", active: false},
  {id: "vector", label: "Vector Stores", icon: "database", active: false},
];

const meta = {
  title: "Shell/Sidebar More Tools",
  component: SidebarMoreTools,
  render: (args) => ({
    components: {SidebarMoreTools},
    setup: () => {
      const open = ref(args.open);
      return {args, open};
    },
    template: '<div style="width:220px;background:var(--card);padding:8px"><SidebarMoreTools v-bind="args" v-model:open="open" /></div>',
  }),
  args: {items, open: true},
} satisfies Meta<typeof SidebarMoreTools>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Open: Story = {};
export const Closed: Story = {args: {open: false}};
