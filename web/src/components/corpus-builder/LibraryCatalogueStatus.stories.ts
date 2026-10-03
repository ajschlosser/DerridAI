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
import LibraryCatalogueStatus from "./LibraryCatalogueStatus.vue";

const status = (
  archive: { status: string; bytes_done: number; total_bytes?: number; error?: string },
  catalogue = { status: "ready", item_count: 70000 },
) => ({ ready: false, search_ready: catalogue.status === "ready", catalogue, archive });

const meta = {
  title: "Corpus Builder/Library/Catalogue Status",
  component: LibraryCatalogueStatus,
  args: {
    status: status({ status: "idle", bytes_done: 0 }),
    catalogueReady: true,
    disabled: false,
    busy: "",
  },
} satisfies Meta<typeof LibraryCatalogueStatus>;

export default meta;
type Story = StoryObj<typeof meta>;

export const CollectionNeeded: Story = {};
export const CatalogueNeeded: Story = {
  args: {
    status: status({ status: "idle", bytes_done: 0 }, { status: "missing", item_count: 0 }),
    catalogueReady: false,
  },
};
export const Downloading: Story = {
  args: {
    status: status({ status: "downloading", bytes_done: 4.2e9, total_bytes: 9.8e9 }),
  },
};
export const FailedWithPartialDownload: Story = {
  args: {
    status: status({
      status: "error",
      bytes_done: 2.1e9,
      total_bytes: 9.8e9,
      error: "Connection reset",
    }),
  },
};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
