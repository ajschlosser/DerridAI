/* Copyright 2026 Aaron John Schlosser, PhD. */

// Compatibility entry point retained for existing imports while the application
// migrates from PDF-specific naming to the media-generic Corpus Builder API.
export * from "./corpus/types";
export { corpusBuilderApi, corpusBuilderApi as pdfCorpusApi } from "./corpus";
