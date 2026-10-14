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
import CorpusTopologyPolicy from "./CorpusTopologyPolicy.vue";

const meta = {
  title: "Corpus Builder/Setup/Topology Policy",
  component: CorpusTopologyPolicy,
  args: {
    modelValue: {
      mode: "source_units",
      source_units_per_record: 1,
      records_per_page: 4,
    },
    syntheticPagesAvailable: true,
    disabled: false,
  },
} satisfies Meta<typeof CorpusTopologyPolicy>;

export default meta;
type Story = StoryObj<typeof meta>;

export const FixedSourceUnits: Story = {};
export const SemanticWithAuthoritativePages: Story = {
  args: {
    modelValue: {
      mode: "semantic",
      source_units_per_record: 1,
      records_per_page: null,
    },
    syntheticPagesAvailable: false,
  },
};
