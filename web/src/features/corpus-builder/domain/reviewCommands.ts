/* Copyright 2026 Aaron John Schlosser, PhD. */

export type CorpusReviewCommand =
  | "previous"
  | "next"
  | "accept"
  | "reject"
  | "needs-attention"
  | "undo"
  | "redo"
  | "focus"
  | "metadata";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return true;
  return Boolean(target.closest('[contenteditable="true"], [role="textbox"]'));
}

/**
 * Convert a keyboard event to a review command without executing domain work.
 *
 * Centralizing this prevents global shortcuts from firing while a researcher is
 * editing text/metadata and gives normal/focus review one command vocabulary.
 */
export function corpusReviewCommandFromKeydown(event: KeyboardEvent): CorpusReviewCommand | null {
  if (
    event.defaultPrevented ||
    event.ctrlKey ||
    event.metaKey ||
    event.altKey ||
    isEditableTarget(event.target)
  )
    return null;

  const key = event.key.toLowerCase();
  if (key === "a") return "accept";
  if (key === "r") return "reject";
  if (key === "n") return "needs-attention";
  if (key === "f") return "focus";
  if (key === "m") return "metadata";
  if (key === "z") return event.shiftKey ? "redo" : "undo";
  if (key === "j" || event.key === "ArrowDown") return "next";
  if (key === "k" || event.key === "ArrowUp") return "previous";
  return null;
}
