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
import PdfPageLabelEditor from "./PdfPageLabelEditor.vue";
const meta: Meta<typeof PdfPageLabelEditor> = {
  title: "Corpus Builder/Source/Printed Page Mapping",
  component: PdfPageLabelEditor,
  args: {
    pages: [
      { pdf_page: 12, printed_page_label: "xii", printed_page_label_source: "visible_folio" },
      { pdf_page: 13, printed_page_label: "1", printed_page_label_source: "visible_folio" },
      { pdf_page: 14, printed_page_label: "2", printed_page_label_source: "inferred_from_folios" },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof PdfPageLabelEditor>;
export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true } };
