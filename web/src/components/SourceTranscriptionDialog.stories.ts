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
import SourceTranscriptionDialog from "./SourceTranscriptionDialog.vue";

const pdfBlocks = [
  {
    block_id: "p00013-b0001",
    page: 13,
    bbox: [40, 80, 500, 260],
    type: "paragraph",
    text: "Extracted source text.",
    extraction_method: "native",
    confidence: 0.99,
  },
];
const audioBlocks = [
  {
    block_id: "audio-0001",
    page: 1,
    bbox: [],
    type: "paragraph",
    text: "The archive recording preserves this sentence for reviewer comparison.",
    extraction_method: "whisper+word-speaker-alignment",
    confidence: 0.84,
    start: 42,
    end: 48,
    speaker: "SPEAKER_1",
    provider_speaker: "SPEAKER_00",
    speaker_assignment: {
      method: "word_overlap",
      confidence: 0.97,
      ambiguous_word_count: 0,
      word_count: 9,
      review_recommended: false,
    },
  },
  {
    block_id: "audio-0002",
    page: 1,
    bbox: [],
    type: "paragraph",
    text: "A second voice begins near the transition.",
    extraction_method: "whisper+word-speaker-alignment",
    confidence: 0.82,
    start: 48,
    end: 52,
    speaker: "SPEAKER_2",
    provider_speaker: "SPEAKER_01",
    speaker_assignment: {
      method: "word_overlap",
      confidence: 0.61,
      ambiguous_word_count: 1,
      word_count: 8,
      review_recommended: true,
    },
  },
];
const longText =
  "A reviewer-entered transcription with an intentionally-long-unbroken-token-that-must-wrap-inside-the-dialog-at-narrow-widths-so-it-does-not-force-horizontal-scrolling.";

const meta = {
  title: "Corpus Builder/Source/Transcription Workspace",
  component: SourceTranscriptionDialog,
  args: {
    open: true,
    mediaKind: "pdf",
    pdfUrl: "/sample.pdf",
    page: 13,
    pageCount: 49,
    printedPage: 1,
    text: "Reviewed record text.",
    blocks: pdfBlocks,
  },
} satisfies Meta<typeof SourceTranscriptionDialog>;
export default meta;
type Story = StoryObj<typeof meta>;

export const PdfReview: Story = {};

export const AudioReview: Story = {
  args: {
    mediaKind: "audio",
    pdfUrl: "",
    audioUrl: "/seminar.wav",
    page: 1,
    pageCount: 1,
    printedPage: null,
    text: "Reviewed audio transcript text.",
    blocks: audioBlocks,
  },
};

export const TextOnlyReview: Story = {
  args: {
    mediaKind: "text",
    pdfUrl: "",
    page: 1,
    pageCount: 1,
    printedPage: null,
    text: longText,
    blocks: [
      { ...audioBlocks[0], block_id: "text-0001", start: undefined, end: undefined, speaker: "" },
    ],
  },
  parameters: { viewport: { defaultViewport: "mobile2" } },
};

export const BusySaving: Story = {
  args: {
    busy: true,
    text: "Saving a reviewed transcription revision.",
  },
};
