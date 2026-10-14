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
import RecordReadingPane from "./RecordReadingPane.vue";
const text =
  "The relation to the other is not merely one relation among others. Responsibility is exposed in the face of the other, and this exposure interrupts the sovereignty of the same.";
const meta = {
  title: "Record Workspace/Reading Pane",
  component: RecordReadingPane,
  args: {
    text,
    findQuery: "other",
    wordCount: 30,
    characterCount: text.length,
    canAnnotate: true,
    annotations: [
      {
        id: "a1",
        field: "text",
        quote: "Responsibility is exposed in the face of the other",
        note: "Useful formulation of responsibility.",
        tags: ["ethics"],
        author: "researcher",
        created_at: "2026-09-14T12:00:00Z",
        removable: true,
      },
    ],
  },
} satisfies Meta<typeof RecordReadingPane>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const ResearcherSummary: Story = { args: { summaryMode: true, canAnnotate: false } };
