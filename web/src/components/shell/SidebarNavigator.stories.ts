/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SidebarNavigator from "./SidebarNavigator.vue";

const groups = [
  {
    section: "Research",
    items: [
      { id: "global", label: "Search", icon: "search", active: true },
      { id: "rag", label: "Research", icon: "spark", active: false },
      { id: "faq", label: "Response Library", icon: "books", active: false },
    ],
  },
  {
    section: "Corpora",
    items: [
      { id: "works", label: "Works", icon: "books", active: false },
      { id: "list", label: "Records", icon: "list", active: false },
      { id: "compare", label: "Compare", icon: "compare", active: false },
      { id: "vector", label: "Corpus Data", icon: "database", active: false },
    ],
  },
  {
    section: "Build",
    items: [
      { id: "pdf", label: "Corpus Builder", icon: "pdf", active: false },
      { id: "sources", label: "Sources", icon: "books", active: false },
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
  title: "Shell/Sidebar Navigator",
  component: SidebarNavigator,
  args: { groups, collapsed: false },
  render: (args) => ({
    components: { SidebarNavigator },
    setup: () => ({ args }),
    template:
      '<div style="width:240px;min-height:720px;background:var(--card);padding:8px"><SidebarNavigator v-bind="args" /></div>',
  }),
} satisfies Meta<typeof SidebarNavigator>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Collapsed: Story = { args: { collapsed: true } };
export const FrenchLengthStress: Story = {
  args: {
    groups: groups.map((group) => ({
      ...group,
      section:
        group.section === "Research"
          ? "Recherche"
          : group.section === "Corpora"
            ? "Corpus"
            : group.section === "Build"
              ? "Construction"
              : "Système",
      items: group.items.map((item) => ({
        ...item,
        label:
          item.id === "responsecache"
            ? "Données système"
            : item.id === "pdf"
              ? "Générateur de corpus"
              : item.label,
      })),
    })),
  },
  parameters: { locale: "fr-CA" },
};
