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
import SettingsNav from "./SettingsNav.vue";
import type { SettingsSectionId } from "../../domain/settings";

const items = [
  { id: "overview" as SettingsSectionId, label: "Overview" },
  { id: "preferences" as SettingsSectionId, label: "Preferences" },
  { id: "research" as SettingsSectionId, label: "Research & review" },
  { id: "retrieval" as SettingsSectionId, label: "Retrieval & indexing" },
  { id: "services" as SettingsSectionId, label: "AI & language services" },
  { id: "data" as SettingsSectionId, label: "Data & storage" },
  { id: "access" as SettingsSectionId, label: "Access & permissions" },
  { id: "troubleshooting" as SettingsSectionId, label: "Troubleshooting & recovery" },
];

const meta = {
  title: "Settings/Navigation",
  component: SettingsNav,
  render: (args) => ({
    components: { SettingsNav },
    setup: () => ({ args }),
    template: `<div style="max-width:240px"><SettingsNav v-bind="args" /></div>`,
  }),
  args: { modelValue: "overview", items, navLabel: "Settings categories" },
} satisfies Meta<typeof SettingsNav>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const French: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    navLabel: "Catégories de paramètres",
    items: [
      { id: "overview", label: "Vue d’ensemble" },
      { id: "preferences", label: "Préférences" },
      { id: "data", label: "Données et stockage" },
    ],
  },
};
