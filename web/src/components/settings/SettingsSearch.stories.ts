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
import { ref } from "vue";
import SettingsSearch from "./SettingsSearch.vue";
import type { SettingsSearchHit } from "./SettingsSearch.vue";

const hits: SettingsSearchHit[] = [
  { id: "rag-k", section: "retrieval", label: "Retrieval k", group: "Vector stores and retrieval" },
  { id: "theme", section: "preferences", label: "Color theme", group: "Preferences" },
];

const meta = {
  title: "Settings/Search",
  component: SettingsSearch,
  render: (args) => ({
    components: { SettingsSearch },
    setup: () => {
      const query = ref(args.modelValue);
      return { args, query };
    },
    template: '<div style="max-width:520px"><SettingsSearch v-bind="args" v-model="query" /></div>',
  }),
  args: {
    modelValue: "retriev",
    results: hits,
    label: "Search settings",
    placeholder: "Find a setting",
    noResults: "No settings match that search.",
    resultCount: "2 matching settings",
  },
} satisfies Meta<typeof SettingsSearch>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Matches: Story = {};
export const Empty: Story = {
  args: { modelValue: "xyzzy", results: [], resultCount: "0 matching settings" },
};
export const French: Story = {
  parameters: { locale: "fr-CA" },
  args: {
    label: "Rechercher dans les paramètres",
    placeholder: "Trouver un paramètre",
    noResults: "Aucun paramètre ne correspond à cette recherche.",
    resultCount: "2 paramètres correspondants",
    results: [
      {
        id: "rag-k",
        section: "retrieval",
        label: "k de repérage",
        group: "Magasins vectoriels et repérage",
      },
    ],
  },
};
