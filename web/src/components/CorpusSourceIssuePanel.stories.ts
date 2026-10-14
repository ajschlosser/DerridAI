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
import CorpusSourceIssuePanel from "./CorpusSourceIssuePanel.vue";
const meta: Meta<typeof CorpusSourceIssuePanel> = {
  title: "Corpus Builder/Review/Source Issue Panel",
  component: CorpusSourceIssuePanel,
};
export default meta;
type Story = StoryObj<typeof CorpusSourceIssuePanel>;
export const Fragmented: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "fragmented_glyph_layout",
        severity: "blocking",
        pages: [1, 2],
        micro_line_ratio: 0.63,
        message: "Extracted text appears fragmented into individual glyphs or punctuation lines.",
      },
    ],
  },
};
export const FrenchLength: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "source_quality_blocking",
        severity: "blocking",
        pages: [14],
        message:
          "La couche de texte du PDF contient des caractères de remplacement ou de contrôle et doit être vérifiée avant l’acceptation savante.",
      },
    ],
  },
};
export const IllegibleText: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "illegible_text",
        severity: "blocking",
        pages: [24],
        noise: 66,
        message: "Extracted text does not look like words in a writing system.",
      },
    ],
  },
};
export const PixelatedScan: Story = {
  args: {
    interactive: true,
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
export const IllegibleAndPixelated: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "illegible_text",
        severity: "blocking",
        pages: [8, 9],
        noise: 72,
        message: "Extracted text does not look like words in a writing system.",
      },
      {
        code: "low_raster_quality",
        severity: "blocking",
        pages: [8, 9],
        message: "Embedded page image resolution is too low to trust as a scholarly scan.",
      },
    ],
  },
};
