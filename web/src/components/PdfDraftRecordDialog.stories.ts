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
import PdfDraftRecordDialog from "./PdfDraftRecordDialog.vue";
import { openPdfDraftRecordDialog } from "../composables/pdfDraftRecordDialog";

const meta = {
  title: "Jobs/PDF Draft Record Dialog",
  component: PdfDraftRecordDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { PdfDraftRecordDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><PdfDraftRecordDialog /></div>`,
    methods: {
      open() {
        openPdfDraftRecordDialog({
          title: "Of Grammatology",
          page: 158,
          recordJson: '{\n  "text": "There is nothing outside the text."\n}',
          files: [{ id: "f1", name: "grammatology.jsonl", count: 120 }],
          stores: [{ id: "derrida", name: "derrida", count: 4200 }],
          save: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof PdfDraftRecordDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithDestinations: Story = {};
