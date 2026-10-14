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
import CorpusRunGuidance from "./CorpusRunGuidance.vue";

const meta = {
  title: "Corpus Builder/Setup/Run Guidance",
  component: CorpusRunGuidance,
  args: {
    fields: [
      { name: "persons", label: "People", group: "indexing" },
      { name: "works_referenced", label: "Works cited in the argument", group: "indexing" },
      { name: "concepts", label: "Concepts", group: "indexing" },
    ],
    modelValue: {
      persons: {
        instructions:
          "Include philosophers whose positions are discussed, not incidental names in references.",
        look_for: ["Emmanuel Levinas", "Levinas"],
        required: true,
      },
      works_referenced: {
        instructions: "Include works treated in the body text.",
        look_for: ["Totality and Infinity"],
      },
    },
  },
} satisfies Meta<typeof CorpusRunGuidance>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Seeded: Story = {};
export const Empty: Story = { args: { modelValue: {} } };
export const Disabled: Story = { args: { disabled: true } };
