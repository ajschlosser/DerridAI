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
import WorksLibraryCard from "./WorksLibraryCard.vue";
import type { WorksItem } from "../../types/works";

const work: WorksItem = {
  work: "Adieu to Emmanuel Levinas",
  count: 318,
  review: 4,
  annotations: 2,
  files: ["adieu.jsonl"],
  authors: ["Jacques Derrida"],
  years: ["1999"],
  cover: "",
  citation: "Derrida, Jacques. Adieu to Emmanuel Levinas. Stanford University Press, 1999.",
  year_label: "1999",
  subtitle: "",
  publisher: {
    field_label: "Publisher",
    value: "Stanford University Press",
    mixed: false,
    unique_count: 0,
  },
  translator: {
    field_label: "Translator",
    value: "Pascale-Anne Brault",
    mixed: false,
    unique_count: 0,
  },
  metadata: [],
  status: { kind: "synced", label: "Synced" },
  insights: [],
};

const meta = {
  title: "Works/Library Card",
  component: WorksLibraryCard,
  args: { work, selected: false, canSync: true, syncDisabledReason: "" },
} satisfies Meta<typeof WorksLibraryCard>;
export default meta;
type Story = StoryObj<typeof WorksLibraryCard>;
export const Default: Story = {};
export const Selected: Story = { args: { selected: true } };
export const NeedsReview: Story = {
  args: { work: { ...work, review: 12, status: { kind: "changed", label: "Pending changes" } } },
};
export const LongTitleMissingCover: Story = {
  args: {
    work: {
      ...work,
      work: "Introduction to Edmund Husserl’s Origin of Geometry: A Translation with Extended Commentary on the Problem of Ideal Objectivity",
      cover: "",
      publisher: { field_label: "Publisher", value: "", mixed: true, unique_count: 3 },
    },
  },
};
export const DatabaseUnavailable: Story = {
  args: {
    canSync: false,
    syncDisabledReason: "Select a corpus database to sync.",
    work: { ...work, status: { kind: "none", label: "No database" } },
  },
};
export const Researcher: Story = {
  args: { mode: "researcher", work: { ...work, subtitle: "Jacques Derrida · 1999" } },
};
