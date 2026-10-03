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
import NavigationCommandPalette from "./NavigationCommandPalette.vue";

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
      { id: "global", label: "Search", icon: "search", active: false },
      { id: "works", label: "Works", icon: "books", active: false },
      { id: "compare", label: "Compare", icon: "compare", active: false },
    ],
  },
  {
    id: "AI & Automation",
    section: "AI & Automation",
    items: [
      { id: "providers", label: "LLM Providers", icon: "spark", active: false },
      { id: "pipelines", label: "Pipeline Studio", icon: "compare", active: false },
    ],
  },
  {
    id: "System",
    section: "System",
    items: [{ id: "responsecache", label: "System Data", icon: "database", active: false }],
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
