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
import SearchFacetPanel from "./SearchFacetPanel.vue";
const facets = [
  {
    field: "work",
    label: "Work",
    values: [
      { value: "Adieu", label: "Adieu", count: 84, selected: true },
      { value: "Rogues", label: "Rogues", count: 51, selected: false },
      { value: "Aporias", label: "Aporias", count: 37, selected: false },
    ],
  },
  {
    field: "needs_review",
    label: "Needs Review",
    values: [
      { value: "true", label: "Needs review", count: 18, selected: false },
      { value: "false", label: "Reviewed", count: 154, selected: false },
    ],
  },
  {
    field: "discourse_role",
    label: "Discourse Role",
    values: [
      { value: "analysis", label: "Analysis", count: 73, selected: false },
      { value: "quotation", label: "Quotation", count: 48, selected: false },
    ],
  },
];
const meta: Meta<typeof SearchFacetPanel> = {
  title: "Search/Facet Panel",
  component: SearchFacetPanel,
  args: { facets },
};
export default meta;
type Story = StoryObj<typeof SearchFacetPanel>;
export const Default: Story = {};
