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
import type { WorksLibraryItem } from "../../types/works";
import WorksLibraryList from "./WorksLibraryList.vue";

function biblio(label: string, value = "") {
  return { field_label: label, value, mixed: false, unique_count: 0 };
}

const works: WorksLibraryItem[] = [
  {
    work: "Adieu to Emmanuel Levinas",
    count: 318,
    review: 4,
    annotations: 2,
    files: ["adieu.jsonl"],
    authors: ["Jacques Derrida"],
    years: ["1999"],
    cover: "",
    year_label: "1999",
    subtitle: "",
    publisher: biblio("Publisher", "Stanford University Press"),
    translator: biblio("Translator", "Pascale-Anne Brault"),
    status: { kind: "changed", label: "Pending changes" },
  },
  {
    work: "Of Grammatology",
    count: 912,
    review: 0,
    annotations: 7,
    files: ["grammatology.jsonl"],
    authors: ["Jacques Derrida"],
    years: ["1976"],
    cover: "",
    year_label: "1976",
    subtitle: "",
    publisher: biblio("Publisher", "Johns Hopkins University Press"),
    translator: biblio("Translator", "Gayatri Chakravorty Spivak"),
    status: { kind: "synced", label: "Synced" },
  },
  {
    work: "Introduction to Edmund Husserl’s Origin of Geometry: A Translation with Extended Commentary on the Problem of Ideal Objectivity",
    count: 144,
    review: 12,
    annotations: 0,
    files: ["origin-geometry.jsonl"],
    authors: ["Jacques Derrida"],
    years: ["1962"],
    cover: "",
    year_label: "1962",
    subtitle: "",
    publisher: biblio("Publisher"),
    translator: biblio("Translator"),
    status: { kind: "absent", label: "Not in DB" },
  },
];

const meta = {
  title: "Works/Library List",
  component: WorksLibraryList,
  args: {
    works,
    selectedWork: "Of Grammatology",
    mode: "admin",
    canSync: true,
    syncDisabledReason: "",
  },
} satisfies Meta<typeof WorksLibraryList>;

export default meta;
type Story = StoryObj<typeof WorksLibraryList>;

export const Admin: Story = {};
export const Researcher: Story = {
  args: {
    mode: "researcher",
    selectedWork: "",
  },
};
export const DatabaseUnavailable: Story = {
  args: {
    canSync: false,
    syncDisabledReason: "No search index is available.",
    works: works.map((work) => ({
      ...work,
      status: { kind: "none", label: "No search index" },
    })),
  },
};
