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

export function sourceMediaKindForFile(file: {
  name?: string;
  type?: string;
}): CorpusMediaKind | "" {
  const name = String(file.name || "")
    .trim()
    .toLowerCase();
  const type = String(file.type || "")
    .trim()
    .toLowerCase();
  if (type === "application/pdf" || name.endsWith(".pdf")) return "pdf";
  if (type.startsWith("image/") || /\.(?:png|jpe?g)$/.test(name)) return "image";
  if (
    type.startsWith("audio/") ||
    type.startsWith("video/") ||
    /\.(?:mp3|wav|m4a|ogg|flac|webm|mp4|mpeg|mpga|aac)$/.test(name)
  )
    return "audio";
  if (
    type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
    name.endsWith(".docx")
  )
    return "docx";
  if (type === "application/rtf" || type === "text/rtf" || name.endsWith(".rtf")) return "rtf";
  if (type === "text/html" || /\.(?:html?|xhtml)$/.test(name)) return "html";
  if (type.startsWith("text/") || /\.(?:txt|text|md)$/.test(name)) return "text";
  return "";
}

export interface SourceMediaCapabilities {
  /** Physical page navigation exists in the extracted source representation. */
  pages: boolean;
  /** Physical PDF pages can be mapped to printed/scholarly page labels. */
  printedPagination: boolean;
  /** The PDF viewer is an appropriate primary source surface. */
  pdfViewer: boolean;
  /** A standalone image viewer is an appropriate primary source surface. */
  imageViewer: boolean;
  /** OCR/image-region affordances are meaningful for this source. */
  imageRegions: boolean;
  /** An audio player is an appropriate primary source surface. */
  audioPlayer: boolean;
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
      imageViewer: false,
      imageRegions: false,
      audioPlayer: true,
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
      imageViewer: true,
      imageRegions: true,
      audioPlayer: false,
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
      imageViewer: false,
      imageRegions: true,
      audioPlayer: false,
      timeSpans: false,
      transcription: false,
      documentLayout: true,
    };
  }

  if (
    normalized === "text" ||
    normalized === "rtf" ||
    normalized === "docx" ||
    normalized === "html" ||
    normalized === "url" ||
    normalized === "gutenberg"
  ) {
    return {
      pages: false,
      printedPagination: false,
      pdfViewer: false,
      imageViewer: false,
      imageRegions: false,
      audioPlayer: false,
      timeSpans: false,
      transcription: true,
      documentLayout: false,
    };
  }

  return {
    pages: false,
    printedPagination: false,
    pdfViewer: false,
    imageViewer: false,
    imageRegions: false,
    audioPlayer: false,
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
