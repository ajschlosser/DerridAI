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
import WorksOverviewCard from "./WorksOverviewCard.vue";
import type { WorksItem } from "../../types/works";

const cover =
  "data:image/svg+xml," +
  encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="400" height="600" viewBox="0 0 400 600">
  <rect width="400" height="600" fill="currentColor"/>
  <rect x="28" y="36" width="344" height="528" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>
  <text x="48" y="280" fill="#fff" font-size="34" font-family="Georgia, serif">Adieu to</text>
  <text x="48" y="328" fill="#fff" font-size="34" font-family="Georgia, serif">Emmanuel Levinas</text>
  <text x="48" y="520" fill="#fff" font-size="16" font-family="Georgia, serif" fill-opacity=".8">Stanford, 1999</text>
</svg>`);

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
  subtitle: "Jacques Derrida · 1999 · Stanford University Press",
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
  metadata: [
    {
      field_id: "derridai.document.document_author",
      field: "document_author",
      field_label: "Document author",
      value: "Jacques Derrida",
      mixed: false,
      unique_count: 0,
      empty: false,
    },
    {
      field_id: "derridai.document.publisher",
      field: "publisher",
      field_label: "Publisher",
      value: "Stanford University Press",
      mixed: false,
      unique_count: 0,
      empty: false,
    },
    {
      field_id: "derridai.document.publication_year",
      field: "publication_year",
      field_label: "Publication year",
      value: "1999",
      mixed: false,
      unique_count: 0,
      empty: false,
    },
  ],
  status: { kind: "synced", label: "Synced" },
  insights: [
    {
      id: "topics",
      field: "topics",
      title: "Top 5 topics in the work",
      heading: "Top 5 topics",
      type: "bars",
      values: [
        { key: "ethics", value: 18 },
        { key: "hospitality", value: 11 },
      ],
    },
    {
      id: "roles",
      field: "discourse_role",
      title: "Top discourse roles as percentage of recorded roles",
      heading: "Top discourse roles as percentage of recorded roles",
      type: "pie",
      values: [
        { key: "analysis", value: 12 },
        { key: "quotation", value: 5 },
      ],
    },
  ],
};

const meta = {
  title: "Works/Overview Card",
  component: WorksOverviewCard,
  args: { work, mode: "admin" as const, citationLabel: "Full citation" },
} satisfies Meta<typeof WorksOverviewCard>;
export default meta;
type Story = StoryObj<typeof WorksOverviewCard>;
export const Admin: Story = {};
export const WithCover: Story = { args: { work: { ...work, cover } } };
export const Researcher: Story = { args: { mode: "researcher" } };
export const InspectorNeedsReview: Story = {
  args: { work: { ...work, review: 12 }, closable: true, canSync: true },
};
export const InDialog: Story = { args: { embedded: true } };
