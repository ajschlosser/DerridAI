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
import CaptureOptionsForm from "./CaptureOptionsForm.vue";

const providerInfo = [
  {
    provider: "gutenberg" as const,
    catalogue_ready: true,
    catalogue_refreshed_at: "2026-09-27T00:00:00Z",
    local_collection_ready: false,
  },
  {
    provider: "wikisource" as const,
    projects: [
      { code: "en", name: "English" },
      { code: "fr", name: "French" },
      { code: "de", name: "German" },
      { code: "es", name: "Spanish" },
    ],
    projects_authoritative: true,
  },
];

const meta = {
  title: "Corpus Builder/Capture/Options",
  component: CaptureOptionsForm,
  args: {
    providers: ["gutenberg", "wikisource"],
    includes: {
      authored: true,
      translations: true,
      translator: false,
      editor: false,
      other: false,
    },
    languages: null,
    providerInfo,
  },
  parameters: { layout: "padded" },
} satisfies Meta<typeof CaptureOptionsForm>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AllLanguages: Story = {};

export const FrenchAndGerman: Story = {
  args: { languages: ["fr", "de"] },
};

export const ContributorRoles: Story = {
  args: {
    includes: {
      authored: true,
      translations: false,
      translator: true,
      editor: true,
      other: true,
    },
  },
};
