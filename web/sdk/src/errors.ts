// Copyright 2026 Aaron John Schlosser, PhD.

export function isAbortError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  if ("name" in error && error.name === "AbortError") return true;
  return typeof DOMException !== "undefined" && error instanceof DOMException && error.name === "AbortError";
}
