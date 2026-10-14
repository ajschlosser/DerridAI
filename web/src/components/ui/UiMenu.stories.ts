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
import UiMenu from "./UiMenu.vue";

const items = [
  { id: "open", label: "Open JSONL", icon: "upload" },
  {
    id: "merge",
    label: "Merge files",
    icon: "plus",
    reason: "Load at least two JSONL files to merge them.",
  },
  { id: "export", label: "Export", icon: "download" },
];

const meta = {
  title: "Foundations/Overlays/Menu",
  component: UiMenu,
  args: { label: "Workspace", items, placement: "bottom", align: "end" },
} satisfies Meta<typeof UiMenu>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const IconOnly: Story = {
  args: {
    icon: "help",
    iconOnly: true,
    label: "Help",
    items: [{ id: "guide", label: "Using DerridAI" }],
  },
};
export const LanguageChoices: Story = {
  args: {
    label: "English",
    ariaLabel: "Interface language, English",
    icon: "language",
    items: [
      { id: "en-US", label: "English", checked: true },
      { id: "fr-CA", label: "Français", checked: false },
    ],
  },
};
