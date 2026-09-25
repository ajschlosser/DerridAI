// Copyright 2026 Aaron John Schlosser, PhD.

export type CorpusMediaKind =
  | "pdf"
  | "image"
  | "audio"
  | "text"
  | "rtf"
  | "docx"
  | "html"
  | "url"
  | "gutenberg"
  | string;

export interface SourceMediaCapabilities {
  /** Physical page navigation exists in the extracted source representation. */
  pages: boolean;
  /** Physical PDF pages can be mapped to printed/scholarly page labels. */
  printedPagination: boolean;
  /** The PDF viewer is an appropriate primary source surface. */
  pdfViewer: boolean;
  /** OCR/image-region affordances are meaningful for this source. */
  imageRegions: boolean;
  /** Time-coded source spans are meaningful for this source. */
  timeSpans: boolean;
  /** Transcript review/editing is meaningful for this source. */
  transcription: boolean;
  /** Page-layout configuration such as two-up reading order is meaningful. */
  documentLayout: boolean;
}

/**
 * Central media capability policy for Corpus Builder.
 *
 * Components should ask what a source can do instead of branching on media
 * names. Unknown/legacy assets retain PDF behavior because pre-media-kind
 * builds were PDF-only.
 */
export function sourceMediaCapabilities(kind?: CorpusMediaKind): SourceMediaCapabilities {
  const normalized = String(kind || "pdf").toLowerCase();

  if (normalized === "audio") {
    return {
      pages: false,
      printedPagination: false,
      pdfViewer: false,
      imageRegions: false,
      timeSpans: true,
      transcription: true,
      documentLayout: false,
    };
  }

  if (normalized === "image") {
    return {
      pages: true,
      printedPagination: false,
      pdfViewer: false,
      imageRegions: true,
      timeSpans: false,
      transcription: false,
      documentLayout: false,
    };
  }

  if (normalized === "pdf") {
    return {
      pages: true,
      printedPagination: true,
      pdfViewer: true,
      imageRegions: true,
      timeSpans: false,
      transcription: false,
      documentLayout: true,
    };
  }

  return {
    pages: false,
    printedPagination: false,
    pdfViewer: false,
    imageRegions: false,
    timeSpans: false,
    transcription: false,
    documentLayout: false,
  };
}

/** Shared source capability retained for existing components. */
export function hasPages(kind?: string) {
  return sourceMediaCapabilities(kind).pages;
}

export function timeLabel(start?: number, end?: number) {
  const clock = (value: number) => {
    const seconds = Math.floor(value);
    return [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60]
      .map((part) => String(part).padStart(2, "0"))
      .join(":");
  };
  return start === undefined || end === undefined ? "" : `${clock(start)}–${clock(end)}`;
}
