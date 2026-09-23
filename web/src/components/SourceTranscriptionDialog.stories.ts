// Copyright 2026 Aaron John Schlosser, PhD.
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
    extraction_method: "whisper",
    confidence: 0.84,
    start: 42,
    end: 48,
    speaker: "SPEAKER_00",
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
    blocks: [{ ...audioBlocks[0], block_id: "text-0001", start: undefined, end: undefined, speaker: "" }],
  },
  parameters: { viewport: { defaultViewport: "mobile2" } },
};

export const BusySaving: Story = {
  args: {
    busy: true,
    text: "Saving a reviewed transcription revision.",
  },
};
