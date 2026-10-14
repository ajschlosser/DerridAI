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
import RecordAnnotations from "./RecordAnnotations.vue";
const meta = {
  title: "Record Workspace/Annotations",
  component: RecordAnnotations,
  args: {
    canAdd: true,
    annotations: [
      {
        id: "1",
        field: "text",
        quote: "I am responsible for the other insofar as he is mortal",
        note: "Compare this with the discussion of substitution.",
        tags: ["Levinas", "responsibility"],
        author: "aaron",
        created_at: "2026-09-14T20:30:00Z",
        removable: true,
      },
      {
        id: "2",
        field: "stance",
        quote: "qualified endorsement",
        note: "The attribution matters here.",
        tags: ["provenance"],
        author: "researcher",
        created_at: "2026-09-13T16:15:00Z",
        removable: false,
      },
    ],
  },
} satisfies Meta<typeof RecordAnnotations>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Empty: Story = { args: { annotations: [] } };
