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

import type { Meta, StoryObj } from "@storybook/vue3";
import CreateSiteDialog from "./CreateSiteDialog.vue";

const meta = {
  title: "Works/CreateSiteDialog",
  component: CreateSiteDialog,
  args: {
    storeName: "derrida-primary",
    works: [
      {
        work: "Glas",
        count: 128,
        authors: ["Jacques Derrida"],
        year_label: "1974",
      },
      {
        work: "Of Grammatology",
        count: 214,
        authors: ["Jacques Derrida"],
        year_label: "1967",
      },
    ],
    initialWork: "Glas",
    languages: [
      { code: "en-US", name: "English", flag: "🇺🇸" },
      { code: "fr-CA", name: "Français", flag: "🇨🇦" },
    ],
    transformersRuntime: {
      version: "4.3.0",
      cached: false,
      download_bytes: 14_871_000,
      inline_bytes: 5_700_000,
    },
    busy: false,
    error: "",
  },
} satisfies Meta<typeof CreateSiteDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const RuntimeCached: Story = {
  args: {
    transformersRuntime: {
      version: "4.3.0",
      cached: true,
      download_bytes: 14_871_000,
      inline_bytes: 5_700_000,
    },
  },
};

export const RuntimeInfoUnavailable: Story = {
  args: { transformersRuntime: undefined },
};

export const Busy: Story = {
  args: { busy: true },
};

export const Error: Story = {
  args: { error: "The selected work is not indexed in this corpus database." },
};
