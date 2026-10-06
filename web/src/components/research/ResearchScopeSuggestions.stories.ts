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
import ResearchScopeSuggestions from "./ResearchScopeSuggestions.vue";

const inventory = async () => ({
  works: [
    { work: "Of Grammatology", authors: ["Jacques Derrida"] },
    { work: "Being and Time", authors: ["Martin Heidegger"] },
  ],
  truncated: false,
});

const meta: Meta<typeof ResearchScopeSuggestions> = {
  title: "Research/Scope suggestions",
  component: ResearchScopeSuggestions,
  parameters: { layout: "padded" },
  args: {
    instructions: "",
    filterExpression: "",
    collection: "derrida_primary",
    fields: ["work", "page_start", "speaker", "year"],
    debounceMs: 0,
    loadInventory: inventory,
  },
};
export default meta;
type Story = StoryObj<typeof ResearchScopeSuggestions>;
export const Empty: Story = {};
export const OnlyAndExclusion: Story = {
  args: { instructions: "Only use Of Grammatology. Exclude Heidegger as speaker." },
};
export const AlreadyAdded: Story = {
  args: {
    instructions: "Only use Of Grammatology.",
    filterExpression: 'work = "Of Grammatology"',
  },
};
export const EmphasisStaysAnInstruction: Story = {
  args: { instructions: "Focus especially on Derrida's early works." },
};
export const UnknownScope: Story = { args: { instructions: "Only use recent essays." } };
