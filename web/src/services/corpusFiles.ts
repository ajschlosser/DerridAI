/* Copyright 2026 Aaron John Schlosser, PhD. */

/** Shell-level request used by workspaces that need the shared corpus file picker. */
export const CHOOSE_CORPUS_FILES_EVENT = "derridai:choose-corpus-files";

export function requestCorpusFiles(): void {
  window.dispatchEvent(new Event(CHOOSE_CORPUS_FILES_EVENT));
}
