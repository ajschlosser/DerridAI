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
import BulkFieldEditorDialog from "./BulkFieldEditorDialog.vue";
import { openBulkFieldEditorDialog } from "../composables/bulkFieldEditorDialog";

const meta = {
  title: "Records/Bulk Field Editor Dialog",
  component: BulkFieldEditorDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { BulkFieldEditorDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><BulkFieldEditorDialog /></div>`,
    methods: {
      open() {
        openBulkFieldEditorDialog({
          title: "Bulk edit field",
          fixedCount: null,
          defaultScope: "active",
          selectedCount: 0,
          activeCount: 1280,
          currentWork: "Of Grammatology",
          allCount: 2220,
          fields: [
            { id: "speaker", label: "Speaker" },
            { id: "needs_review", label: "Needs review" },
          ],
          inspect: () => ({ targets: 1280, distinct: 1, only: "Derrida" }),
          apply: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof BulkFieldEditorDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ActiveTab: Story = {};
