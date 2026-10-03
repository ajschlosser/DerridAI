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
import ComparePicker from "./ComparePicker.vue";

const meta = {
  title: "Compare/Picker",
  component: ComparePicker,
  args: {
    modelValue: "f::0",
    options: [
      { value: "f::0", label: "tab.jsonl · r-a · Glas" },
      { value: "f::1", label: "tab.jsonl · r-b · Voice and Phenomenon" },
    ],
    label: "Find a loaded record",
    placeholder: "Type record ID, work, author, or file…",
    selectedHint: "Selected · tab.jsonl · r-a · Glas",
    emptyHint: "Start typing to search loaded records.",
    noMatches: "No matching records.",
    clearLabel: "Clear",
  },
} satisfies Meta<typeof ComparePicker>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Empty: Story = {
  args: {
    modelValue: "",
    options: [],
    emptyHint: "Load JSONL files or browse the corpus database first.",
  },
};
