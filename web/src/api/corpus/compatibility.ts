/* Copyright 2026 Aaron John Schlosser, PhD. */

/**
 * Compatibility boundary for the legacy PDF-named backend routes.
 * New frontend/domain code is media-generic; only this adapter knows that
 * the server still exposes Corpus Builder operations beneath /api/pdf.
 */
export const LEGACY_CORPUS_BASE = "/api/pdf";

export function legacyCorpusUrl(path: string): string {
  return `${LEGACY_CORPUS_BASE}/${path.replace(/^\\/+/, "")}`;
}
