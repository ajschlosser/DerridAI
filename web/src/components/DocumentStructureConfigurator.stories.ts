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
import DocumentStructureConfigurator from "./DocumentStructureConfigurator.vue";
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
const asset: any = {
  asset_id: "pdf-demo",
  sha256: "x",
  filename: "bilingual-book.pdf",
  created_at: "",
  page_count: 120,
  block_count: 400,
  ocr_pages: 0,
  warnings: [],
  metadata: {},
  document_layout: {
    page_layout: "two_up",
    reading_order: "left_to_right",
    main_text_pdf_start: 8,
    main_text_printed_start: 1,
    main_text_slot: "left",
    bibliography_pdf_start: 110,
    thread_mode: "left_right",
    thread_a_language: "fr_fr",
    thread_b_language: "en_us",
  },
  pages: [
    {
      pdf_page: 8,
      width: 612,
      height: 792,
      logical_pages: [
        { slot: "left", printed_page_label: "1" },
        { slot: "right", printed_page_label: "2" },
      ],
    },
  ],
};
const meta = {
  title: "Corpus Builder/Source/Document Structure & Pagination",
  component: DocumentStructureConfigurator,
  args: { asset, pdfUrl: "/sample.pdf", blocks: [] },
} satisfies Meta<typeof DocumentStructureConfigurator>;
export default meta;
type Story = StoryObj<typeof meta>;
export const TwoUpBilingual: Story = {};
export const MarginColumn: Story = {
  args: {
    asset: {
      ...asset,
      filename: "glossed-edition.pdf",
      document_layout: {
        page_layout: "single",
        reading_order: "left_to_right",
        main_text_pdf_start: 8,
        main_text_printed_start: 1,
        thread_mode: "continuous",
        layout_regions: [
          {
            id: "main",
            role: "main",
            thread: "thread_a",
            flow: "with_main",
            x0: 0,
            y0: 0,
            x1: 1,
            y1: 1,
            applies_to: "all",
          },
          {
            id: "margin",
            role: "margin_apparatus",
            thread: "thread_b",
            flow: "separate",
            x0: 0,
            y0: 0.04,
            x1: 0.2,
            y1: 0.96,
            applies_to: "all",
          },
        ],
      },
    },
  },
};

export const SinglePage: Story = {
  args: {
    asset: {
      ...asset,
      document_layout: {
        page_layout: "single",
        reading_order: "left_to_right",
        main_text_pdf_start: 8,
        main_text_printed_start: 1,
        thread_mode: "continuous",
      },
    },
  },
};

export const NarrowLaptop: Story = {
  decorators: [() => ({ template: '<div style="max-width:860px"><story /></div>' })],
};
