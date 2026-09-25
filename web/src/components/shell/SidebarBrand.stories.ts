/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SidebarBrand from "./SidebarBrand.vue";

const meta = {
  title: "Shell/Sidebar Brand",
  component: SidebarBrand,
  render: (args) => ({
    components: { SidebarBrand },
    setup: () => ({ args }),
    template:
      '<div style="width:220px;background:var(--card);padding:8px"><SidebarBrand v-bind="args" /></div>',
  }),
  args: { collapsed: false },
} satisfies Meta<typeof SidebarBrand>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Expanded: Story = {};
export const Collapsed: Story = { args: { collapsed: true } };
