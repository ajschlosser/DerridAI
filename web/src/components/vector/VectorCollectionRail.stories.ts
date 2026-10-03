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
import VectorCollectionRail from "./VectorCollectionRail.vue";
const collections = [
  { name: "derrida-primary", count: 12840, retrieval_mode: "hybrid", status: "ready" },
  {
    name: "derrida_en",
    count: 6120,
    retrieval_mode: "semantic",
    status: "ready",
    collection_role: "language",
  },
];
const meta = {
  title: "Corpus Data/Collection Rail",
  component: VectorCollectionRail,
  args: { collections, activeName: "derrida-primary", filter: "" },
} satisfies Meta<typeof VectorCollectionRail>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Populated: Story = {};
export const FilteredEmpty: Story = { args: { collections: [], filter: "zzz" } };

export const ProvidersUnavailable: Story = {
  args: {
    canCreate: false,
    createDisabledReason: "Provider choices are unavailable. Retry before creating a collection.",
  },
};
