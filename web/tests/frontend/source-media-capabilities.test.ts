/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { sourceMediaCapabilities } from "../../src/domain/sourceMedia";

describe("Corpus Builder source capabilities", () => {
  it("keeps printed pagination and the PDF viewer PDF-specific", () => {
    const pdf = sourceMediaCapabilities("pdf");
    expect(pdf.printedPagination).toBe(true);
    expect(pdf.pdfViewer).toBe(true);
    expect(pdf.audioPlayer).toBe(false);
  });

  it("models images as regions without pretending they have scholarly pagination", () => {
    const image = sourceMediaCapabilities("image");
    expect(image.pages).toBe(true);
    expect(image.imageViewer).toBe(true);
    expect(image.imageRegions).toBe(true);
    expect(image.printedPagination).toBe(false);
  });

  it("models audio with time spans and transcription instead of page concepts", () => {
    const audio = sourceMediaCapabilities("audio");
    expect(audio.pages).toBe(false);
    expect(audio.timeSpans).toBe(true);
    expect(audio.transcription).toBe(true);
    expect(audio.audioPlayer).toBe(true);
  });

  it("keeps text-like sources free of PDF/audio-only affordances", () => {
    const text = sourceMediaCapabilities("text");
    expect(text.pages).toBe(false);
    expect(text.pdfViewer).toBe(false);
    expect(text.audioPlayer).toBe(false);
  });
});
