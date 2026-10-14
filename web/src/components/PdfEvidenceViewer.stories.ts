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
import PdfEvidenceViewer from "./PdfEvidenceViewer.vue";

const meta: Meta<typeof PdfEvidenceViewer> = {
  title: "Corpus Builder/Source/PDF Evidence Viewer",
  component: PdfEvidenceViewer,
  args: { pdfUrl: "", page: 1, pageWidth: 612, pageHeight: 792, blocks: [], evidenceBlockIds: [] },
};
export default meta;
type Story = StoryObj<typeof PdfEvidenceViewer>;
export const Empty: Story = {};
export const EvidenceGeometry: Story = {
  args: {
    blocks: [
      {
        block_id: "p00001-b0001",
        page: 1,
        bbox: [72, 96, 540, 160],
        type: "paragraph",
        text: "Source block",
        extraction_method: "native",
        confidence: 1,
      },
    ],
    evidenceBlockIds: ["p00001-b0001"],
  },
};
