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
import HelpSearchHero from "./HelpSearchHero.vue";

const meta = {
  title: "Help Center/Search hero",
  component: HelpSearchHero,
  args: {
    modelValue: "",
    searching: false,
    matchCount: 0,
    pageCount: 31,
    termCount: 94,
    questionCount: 54,
    isAdmin: true,
  },
} satisfies Meta<typeof HelpSearchHero>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Administrator: Story = {};

export const Researcher: Story = {
  args: {
    pageCount: 11,
    questionCount: 20,
    isAdmin: false,
  },
};

export const SearchResults: Story = {
  args: {
    modelValue: "pipeline trace",
    searching: true,
    matchCount: 6,
  },
};

export const NarrowViewport: Story = {
  args: {
    modelValue: "FieldAssertion and evidence provenance",
    searching: true,
    matchCount: 8,
  },
  parameters: {
    viewport: { defaultViewport: "mobile1" },
  },
};
