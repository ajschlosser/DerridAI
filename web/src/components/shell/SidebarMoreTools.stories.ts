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
import { ref } from "vue";
import SidebarMoreTools from "./SidebarMoreTools.vue";
import type { SidebarNavEntry } from "./sidebarNav";

const items: SidebarNavEntry[] = [
  { id: "list", label: "Records", icon: "list", active: false },
  { id: "pdf", label: "Corpus Builder", icon: "pdf", active: false },
  { id: "vector", label: "Corpus Data", icon: "database", active: false },
];

const meta = {
  title: "Shell/Sidebar More Tools",
  component: SidebarMoreTools,
  render: (args) => ({
    components: { SidebarMoreTools },
    setup: () => {
      const open = ref(args.open);
      return { args, open };
    },
    template:
      '<div style="width:220px;background:var(--card);padding:8px"><SidebarMoreTools v-bind="args" v-model:open="open" /></div>',
  }),
  args: { items, open: true },
} satisfies Meta<typeof SidebarMoreTools>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Open: Story = {};
export const Closed: Story = { args: { open: false } };
