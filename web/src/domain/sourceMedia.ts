// Copyright 2026 Aaron John Schlosser, PhD.
/** Shared source capabilities: legacy assets without a kind are PDFs. */
export function hasPages(kind?: string) {
  return !kind || kind === "pdf" || kind === "image";
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
