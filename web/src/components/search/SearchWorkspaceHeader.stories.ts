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
import SearchWorkspaceHeader from "./SearchWorkspaceHeader.vue";

const meta = {
  title: "Search/Workspace Header",
  component: SearchWorkspaceHeader,
  args: {
    scope: "loaded",
    totalLoaded: 1842,
    databaseCount: 3,
    selectedEvidence: 7,
    canUseLoaded: true,
    researcher: false,
  },
} satisfies Meta<typeof SearchWorkspaceHeader>;
export default meta;
type Story = StoryObj<typeof SearchWorkspaceHeader>;
export const LoadedRecords: Story = {};
export const DatabaseScope: Story = { args: { scope: "database" } };
export const Researcher: Story = {
  args: { scope: "database", researcher: true, canUseLoaded: false, totalLoaded: 0 },
};
