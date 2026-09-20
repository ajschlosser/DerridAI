/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SidebarPrimaryNav from "./SidebarPrimaryNav.vue";
import type { SidebarNavEntry } from "./sidebarNav";

const items: SidebarNavEntry[] = [
  {id: "home", label: "Home", icon: "dashboard", active: true},
  {id: "global", label: "Search", icon: "search", active: false},
  {id: "works", label: "Works", icon: "books", active: false},
  {id: "record", label: "Record View", icon: "record", active: false},
  {id: "rag", label: "Research", icon: "spark", active: false, disabledReason: "Create a corpus database before starting research."},
];

const meta = {
  title: "Shell/Sidebar Primary Nav",
  component: SidebarPrimaryNav,
  render: (args) => ({
    components: {SidebarPrimaryNav},
    setup: () => ({args}),
    template: '<div style="width:220px;background:var(--card);padding:8px"><SidebarPrimaryNav v-bind="args" /></div>',
  }),
  args: {items},
} satisfies Meta<typeof SidebarPrimaryNav>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
