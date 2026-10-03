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
import CorpusSourceQualityDialog from "./CorpusSourceQualityDialog.vue";

const meta = {
  title: "Corpus Builder/Review/Source Quality Dialog",
  component: CorpusSourceQualityDialog,
  args: {
    open: true,
    extractionNoise: {
      page_count: 12,
      unusable_page_count: 3,
      unusable_page_ratio: 0.25,
      median_noise: 52,
      threshold: 45,
      exceeds_threshold: true,
    },
    issues: [
      {
        code: "illegible_text",
        severity: "blocking",
        pages: [24],
        message: "Extracted text does not look like words in a writing system.",
      },
    ],
  },
} satisfies Meta<typeof CorpusSourceQualityDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const IngestWarning: Story = {};
export const RecordWarning: Story = {
  args: {
    extractionNoise: null,
    issues: [
      {
        code: "low_raster_quality",
        severity: "blocking",
        pages: [8],
        message: "Embedded page image resolution is too low to trust as a scholarly scan.",
      },
    ],
  },
};
