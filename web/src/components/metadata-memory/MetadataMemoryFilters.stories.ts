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
import MetadataMemoryFilters from "./MetadataMemoryFilters.vue";

const facets = {
  fields: ["position_holder", "quoted_position_holder", "proposition_status"],
  kinds: ["positive", "correction"],
  languages: ["en", "fr"],
  builds: ["derrida-cosmopolitanism-2026", "derrida-gift-of-death-2026"],
};

const meta = {
  title: "Metadata memory/Filters",
  component: MetadataMemoryFilters,
  args: {
    query: "",
    field: "",
    kind: "",
    buildId: "",
    language: "",
    facets,
  },
} satisfies Meta<typeof MetadataMemoryFilters>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const ActiveFilters: Story = {
  args: {
    query: "hospitality",
    field: "position_holder",
    kind: "correction",
    buildId: "derrida-cosmopolitanism-2026",
    language: "fr",
  },
};

export const LongValues: Story = {
  args: {
    query:
      "responsabilité, hospitalité et attribution propositionnelle dans un contexte documentaire",
    field: "quoted_position_holder",
    buildId: "derrida-cosmopolitanism-2026",
    language: "fr",
  },
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
