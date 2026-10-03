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
import WorksCorpusContext from "./WorksCorpusContext.vue";

const meta = {
  title: "Works/Corpus Context",
  component: WorksCorpusContext,
  args: {
    mode: "admin",
    stores: [
      { name: "derrida_primary", count: 3102 },
      { name: "derrida_secondary", count: 880 },
    ],
    activeStore: "derrida_primary",
    activeStoreCount: 3102,
    sourceFileCount: 4,
    totalRecords: 3218,
    indexFreshness: {
      state: "stale",
      totalRecords: 3218,
      currentRecords: 3102,
      changedRecords: 84,
      presentRecords: 0,
      absentRecords: 32,
      unknownRecords: 0,
      unavailableRecords: 0,
    },
    storesEmptyLabel: "No search indexes available",
    dbUnavailableReason: "",
    canSyncAll: true,
    syncAllDisabledReason: "",
  },
} satisfies Meta<typeof WorksCorpusContext>;
export default meta;
type Story = StoryObj<typeof WorksCorpusContext>;
export const Admin: Story = {};
export const NoDatabase: Story = {
  args: {
    stores: [],
    activeStore: "",
    activeStoreCount: 0,
    indexFreshness: {
      state: "unavailable",
      totalRecords: 3218,
      currentRecords: 0,
      changedRecords: 0,
      presentRecords: 0,
      absentRecords: 0,
      unknownRecords: 0,
      unavailableRecords: 3218,
    },
    canSyncAll: false,
    dbUnavailableReason: "No corpus database is available.",
    syncAllDisabledReason: "No corpus database is available.",
  },
};
export const Researcher: Story = { args: { mode: "researcher" } };
