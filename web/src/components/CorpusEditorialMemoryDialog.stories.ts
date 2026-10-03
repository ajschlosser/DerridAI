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
import CorpusEditorialMemoryDialog from "./CorpusEditorialMemoryDialog.vue";
const memory = {
  conventions: { discourse_role: { value: "reported_position", confirmed_records: 5 } },
  examples: {
    discourse_role: [
      {
        record_id: "r-17",
        value: "reported_position",
        similarity: 0.72,
        excerpt:
          "Derrida introduces a proposition attributed to Heidegger before turning to his own analysis.",
      },
    ],
  },
  convention_count: 1,
  example_count: 1,
};
const meta = {
  title: "Corpus Builder/Review/Editorial Memory",
  component: CorpusEditorialMemoryDialog,
  args: { open: true, memory },
} satisfies Meta<typeof CorpusEditorialMemoryDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Active: Story = {};
export const Empty: Story = {
  args: { memory: { conventions: {}, examples: {}, convention_count: 0, example_count: 0 } },
};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
