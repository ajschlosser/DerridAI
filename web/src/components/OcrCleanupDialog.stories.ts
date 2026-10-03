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
import OcrCleanupDialog from "./OcrCleanupDialog.vue";
import { openOcrCleanupDialog } from "../composables/ocrCleanupDialog";

const meta = {
  title: "Records/OCR Cleanup Dialog",
  component: OcrCleanupDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { OcrCleanupDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><OcrCleanupDialog /></div>`,
    methods: {
      open() {
        openOcrCleanupDialog({
          active: { name: "of-grammatology.jsonl", recordCount: 1280 },
          selectedCount: 0,
          reviewCount: 42,
          allCount: 2220,
          fileCount: 2,
          choose: async () => undefined,
        });
      },
    },
  }),
} satisfies Meta<typeof OcrCleanupDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const NothingSelected: Story = {};
