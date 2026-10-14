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
import RolePermissionMatrix from "../components/RolePermissionMatrix.vue";
import type { CapabilityDefinition } from "../api/auth";

const catalog: CapabilityDefinition[] = [
  {
    id: "page.dashboard",
    category: "Pages",
    label: "Dashboard",
    description: "Open the dashboard.",
    configurable: true,
  },
  {
    id: "page.research",
    category: "Pages",
    label: "Research",
    description: "Open the Research workspace.",
    configurable: true,
  },
  {
    id: "rag.run",
    category: "Research",
    label: "Run Research",
    description: "Start evidence-grounded Research jobs.",
    configurable: true,
  },
  {
    id: "corpus.read",
    category: "Corpus",
    label: "Read corpus",
    description: "Read researcher-safe corpus records.",
    configurable: true,
  },
  {
    id: "corpus.search",
    category: "Corpus",
    label: "Search corpus",
    description: "Search protected corpus records.",
    configurable: true,
  },
  {
    id: "users.manage",
    category: "Administration",
    label: "Manage users",
    description: "Administrator-only account management.",
    configurable: false,
  },
];

const meta = {
  title: "System/Role Permission Matrix",
  component: RolePermissionMatrix,
  render: (args) => ({
    components: { RolePermissionMatrix },
    setup: () => {
      const selected = ref([...args.modelValue]);
      return { args, selected };
    },
    template: `<RolePermissionMatrix v-bind="args" v-model="selected" />`,
  }),
  args: {
    modelValue: ["page.dashboard", "corpus.read"],
    capabilities: catalog,
    disabled: false,
    filter: "",
  },
} satisfies Meta<typeof RolePermissionMatrix>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};

export const ResearchFocused: Story = {
  args: {
    modelValue: ["page.dashboard", "page.research", "rag.run", "corpus.read", "corpus.search"],
  },
};

export const ReadOnlyCustomRole: Story = {
  args: {
    modelValue: ["page.dashboard", "corpus.read"],
    capabilities: catalog.filter((item) => item.configurable),
  },
};

export const AdministratorLocked: Story = {
  args: {
    modelValue: catalog.map((item) => item.id),
    disabled: true,
  },
};

export const Filtered: Story = {
  args: {
    filter: "research",
    modelValue: ["page.research", "rag.run"],
  },
};
