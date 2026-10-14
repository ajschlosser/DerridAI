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
import RecordHistoryTimeline from "./RecordHistoryTimeline.vue";
const meta = {
  title: "Record Workspace/History Timeline",
  component: RecordHistoryTimeline,
  args: {
    total: 17,
    canOpen: true,
    items: [
      {
        id: "1",
        field_name: "speaker",
        timestamp: "2026-09-14T20:00:00Z",
        source: "manual",
        initiated_by: "admin",
      },
      {
        id: "2",
        field_name: "text",
        timestamp: "2026-09-14T19:30:00Z",
        source: "ocr_cleanup",
        initiated_by: "admin",
      },
      {
        id: "3",
        field_name: "concepts",
        timestamp: "2026-09-14T18:10:00Z",
        source: "record_workspace",
        initiated_by: "admin",
      },
    ],
  },
} satisfies Meta<typeof RecordHistoryTimeline>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
