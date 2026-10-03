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
import RecordInspector from "./RecordInspector.vue";
const snapshot = {
  available: true,
  mode: "workspace" as const,
  record_id: "adieu-00042",
  record: {
    document_author: "Jacques Derrida",
    edition: "Stanford University Press",
    year: 1999,
    page_start: 20,
    page_end: 21,
    document_language: "en",
    original_language: "fr",
    speaker: "Derrida",
    position_holder: "Levinas",
    stance: "qualified endorsement",
    target: "Heidegger",
    discourse_role: "analysis",
    proposition_status: "attributed claim",
    topics: ["ethics", "death"],
    concepts: ["responsibility", "the Other"],
    persons: ["Levinas", "Heidegger"],
    works_referenced: ["Being and Time"],
  },
  annotations: [],
  pdf_links: [{ pdf_file: "adieu.pdf", pdf_page: 33 }],
  history: [],
  history_count: 5,
  inline_citation: "(Derrida 1999: 20-21)",
  full_citation:
    "Derrida, Jacques. Adieu to Emmanuel Levinas. Stanford University Press, 1999, pp. 20–21.",
  capabilities: {
    edit: true,
    annotate: true,
    evidence: true,
    review: true,
    upsert: true,
    llm_review: true,
    pdf: true,
    history: true,
    copy: true,
  },
  pdf: {
    loaded: true,
    related: true,
    current_page: 33,
    title: "Record Workspace/Inspector",
    name: "adieu.pdf",
  },
};
const meta = {
  title: "Record Workspace/Inspector",
  component: RecordInspector,
  args: { snapshot },
} satisfies Meta<typeof RecordInspector>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
