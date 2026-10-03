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
import SearchAdvancedFilters from "./SearchAdvancedFilters.vue";

const meta = {
  title: "Search/Advanced filters",
  component: SearchAdvancedFilters,
  args: {
    filters: [
      {
        id: "f1",
        field: "work",
        field_label: "Work",
        op: "eq",
        op_label: "is",
        value: "Of Grammatology",
      },
    ],
    fields: [
      { key: "work", label: "Work", kind: "text" },
      { key: "speaker", label: "Speaker", kind: "text" },
    ],
    schemas: [
      {
        id: "default",
        name: "Default",
        description: "",
        builtin: true,
        field_count: 12,
        groups: [],
        hash: "h",
      },
    ],
    schemaId: "default",
    associatedSchemaId: "default",
    field: "speaker",
    op: "eq",
    value: "",
    ops: [
      ["eq", "search.op_eq", "is"],
      ["contains", "search.op_contains", "contains"],
    ],
    suggestions: ["Derrida", "Levinas"],
  },
} satisfies Meta<typeof SearchAdvancedFilters>;
export default meta;
type Story = StoryObj<typeof meta>;
export const WithCondition: Story = {};
export const Empty: Story = { args: { filters: [] } };
