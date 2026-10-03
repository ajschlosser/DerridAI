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
import HelpContentsNav from "./HelpContentsNav.vue";

const meta = {
  title: "Help Center/Contents navigation",
  component: HelpContentsNav,
  args: {
    links: [
      { id: "help-pages", icon: "list", label: "Product guide", count: 31 },
      { id: "help-glossary", icon: "books", label: "Technical glossary & parameter reference", count: 94 },
      { id: "help-questions", icon: "help", label: "Common workflow questions", count: 54 },
    ],
    activeSection: "help-pages",
  },
} satisfies Meta<typeof HelpContentsNav>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const GlossaryActive: Story = {
  args: { activeSection: "help-glossary" },
};

export const NarrowViewport: Story = {
  parameters: {
    viewport: { defaultViewport: "mobile1" },
  },
};
