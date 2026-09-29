/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import NavigationCommandPalette from "./NavigationCommandPalette.vue";

const groups = [
  {
    section: "Research",
    items: [
      { id: "global", label: "Search", icon: "search", active: false },
      { id: "rag", label: "Research", icon: "spark", active: false },
    ],
  },
  {
    section: "Corpora",
    items: [
      { id: "works", label: "Works", icon: "books", active: false },
      { id: "compare", label: "Compare", icon: "compare", active: false },
    ],
  },
  {
    section: "System",
    items: [
      { id: "responsecache", label: "System Data", icon: "database", active: false },
      { id: "config", label: "Settings", icon: "gear", active: false },
    ],
  },
];

const meta = {
  title: "Shell/Navigation Command Palette",
  component: NavigationCommandPalette,
  args: { groups },
  render: (args) => ({
    components: { NavigationCommandPalette },
    setup: () => ({ args }),
    template:
      '<div style="padding:24px"><NavigationCommandPalette ref="palette" v-bind="args" /><button class="btn" type="button" @click="($refs.palette as any).open()">Open command palette</button></div>',
  }),
} satisfies Meta<typeof NavigationCommandPalette>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const French: Story = { parameters: { locale: "fr-CA" } };
