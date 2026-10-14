/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SidebarNavigator from "./SidebarNavigator.vue";

const groups = [
  {
    id: "Research",
    section: "Research",
    items: [
      { id: "rag", label: "Research", icon: "spark", active: false },
      { id: "faq", label: "Response Library", icon: "books", active: false },
    ],
  },
  {
    id: "Corpora",
    section: "Corpora",
    items: [
      { id: "global", label: "Search", icon: "search", active: true },
      { id: "works", label: "Works", icon: "books", active: false },
      { id: "list", label: "Records", icon: "list", active: false },
      { id: "compare", label: "Compare", icon: "compare", active: false },
    ],
  },
  {
    id: "Corpus Management",
    section: "Corpus Management",
    items: [
      { id: "sources", label: "Sources", icon: "books", active: false },
      { id: "pdf", label: "Corpus Builder", icon: "pdf", active: false },
      { id: "vector", label: "Corpus Data", icon: "database", active: false },
      { id: "schemas", label: "Metadata schemas", icon: "list", active: false },
    ],
  },
  {
    id: "AI & Automation",
    section: "AI & Automation",
    items: [
      { id: "providers", label: "LLM Providers", icon: "spark", active: false },
      { id: "pipelines", label: "Pipeline Studio", icon: "compare", active: false },
      { id: "metadatamemory", label: "Metadata memory", icon: "spark", active: false },
    ],
  },
  {
    id: "System",
    section: "System",
    items: [
      { id: "responsecache", label: "System Data", icon: "database", active: false },
      { id: "users", label: "Users & roles", icon: "users", active: false },
      { id: "languages", label: "Languages", icon: "language", active: false },
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
            : group.section === "Corpus Management"
              ? "Gestion des corpus"
              : group.section === "AI & Automation"
                ? "IA et automatisation"
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
