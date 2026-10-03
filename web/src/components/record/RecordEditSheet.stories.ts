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
import RecordEditSheet from "./RecordEditSheet.vue";

const record = {
  work: "Adieu to Emmanuel Levinas",
  document_author: "Jacques Derrida",
  publication_year: 1999,
  publisher: "Stanford University Press",
  translator: "Pascale-Anne Brault and Michael Naas",
  page_start: 20,
  page_end: 21,
  speaker: "Derrida",
  position_holder: "Levinas",
  stance: "qualified endorsement",
  discourse_role: "analysis",
  concepts: ["responsibility", "the Other"],
  topics: ["ethics", "death"],
  needs_review: false,
  text: "Responsibility is exposed in the face of the other.",
};
const meta = {
  title: "Record Workspace/Edit Sheet",
  component: RecordEditSheet,
  args: { open: true, record },
} satisfies Meta<typeof RecordEditSheet>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
