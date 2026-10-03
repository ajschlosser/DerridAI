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
import CorpusSourceSummary from "./CorpusSourceSummary.vue";
const blocks = [
  {
    block_id: "p00001-b0001",
    page: 1,
    bbox: [60, 80, 540, 220],
    type: "paragraph",
    text: "A source block used to verify the record.",
    extraction_method: "native",
    confidence: 1,
  },
];
const meta = {
  title: "Corpus Builder/Source/Compact Source Summary",
  component: CorpusSourceSummary,
  args: {
    pdfUrl: "",
    page: 1,
    pageCount: 75,
    pageWidth: 612,
    pageHeight: 792,
    blocks,
    canPrevious: false,
    canNext: true,
  },
} satisfies Meta<typeof CorpusSourceSummary>;
export default meta;
type Story = StoryObj<typeof meta>;
export const NarrowInspector: Story = { parameters: { viewport: { defaultViewport: "mobile2" } } };
export const SourceUnavailable: Story = { args: { pdfUrl: "", blocks: [] } };

export const AudioSpans: Story = {
  args: {
    mediaKind: "audio",
    pdfUrl: "",
    audioUrl: "/seminar.wav",
    page: 1,
    pageCount: 1,
    blocks: [
      {
        block_id: "audio-1",
        page: 1,
        bbox: [],
        type: "paragraph",
        text: "The source transcript remains unchanged.",
        extraction_method: "whisper",
        confidence: 0.8,
        start: 1,
        end: 4,
        speaker: "SPEAKER_00",
      },
    ],
  },
};
export const TextSpans: Story = { args: { mediaKind: "text", pdfUrl: "", page: 1 } };
