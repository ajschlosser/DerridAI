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
import WorksLibraryToolbar from "./WorksLibraryToolbar.vue";

const meta = {
  title: "Works/Library Toolbar",
  component: WorksLibraryToolbar,
  args: {
    mode: "admin",
    query: "",
    sort: "title-asc",
    filters: { needsReview: false, dbStatus: "", author: "" },
    viewMode: "cards",
    authors: ["Jacques Derrida", "Emmanuel Levinas"],
    totalWorks: 64,
    visibleWorks: 64,
    totalReview: 7,
  },
} satisfies Meta<typeof WorksLibraryToolbar>;
export default meta;
type Story = StoryObj<typeof WorksLibraryToolbar>;
export const Default: Story = {};
export const Filtered: Story = {
  args: {
    query: "gla",
    visibleWorks: 1,
    filters: { needsReview: true, dbStatus: "changed", author: "" },
    viewMode: "list",
  },
};
export const Researcher: Story = { args: { mode: "researcher", totalReview: 0 } };
