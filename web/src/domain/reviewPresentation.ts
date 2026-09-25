/* Copyright 2026 Aaron John Schlosser, PhD. */
import { diffWordsWithSpace } from "diff";
import { esc } from "./html";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Diff sides, JSON display and small HTML fragments for review dialogs. Moved verbatim from the legacy runtime.

export function reviewDiffSides(current: unknown, proposed: unknown) {
  const leftText = jsonPretty(current);
  const rightText = jsonPretty(proposed);
  const parts = diffWordsWithSpace(leftText, rightText);
  const left = parts
    .filter((part) => !part.added)
    .map((part) => (part.removed ? `<span class="del">${esc(part.value)}</span>` : esc(part.value)))
    .join("");
  const right = parts
    .filter((part) => !part.removed)
    .map((part) => (part.added ? `<span class="ins">${esc(part.value)}</span>` : esc(part.value)))
    .join("");
  return { left, right };
}

export function llmDiffSides(field: string, current: unknown, proposed: unknown) {
  if (field !== "text") return null;
  const parts = diffWordsWithSpace(String(current ?? ""), String(proposed ?? ""));
  const left = parts
    .filter((part) => !part.added)
    .map((part) => (part.removed ? `<span class="del">${esc(part.value)}</span>` : esc(part.value)))
    .join("");
  const right = parts
    .filter((part) => !part.removed)
    .map((part) => (part.added ? `<span class="ins">${esc(part.value)}</span>` : esc(part.value)))
    .join("");
  return { left, right };
}

export function llmDiffSummary(current: unknown, proposed: unknown) {
  const parts = diffWordsWithSpace(String(current ?? ""), String(proposed ?? ""));
  const countWords = (value: string) => (value.trim() ? value.trim().split(/\s+/).length : 0);
  return {
    removed: parts
      .filter((part) => part.removed)
      .reduce((total, part) => total + countWords(part.value), 0),
    added: parts
      .filter((part) => part.added)
      .reduce((total, part) => total + countWords(part.value), 0),
    before: countWords(String(current ?? "")),
    after: countWords(String(proposed ?? "")),
  };
}

export function jsonPretty(value: unknown): string {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function ragAnswerHtml(text: unknown): string {
  const value = String(text || "").trim();
  if (!value) return '<div class="llm-empty">No answer returned.</div>';
  return value
    .split(/\n{2,}/)
    .map((block) => {
      const trimmed = block.trim();
      if (!trimmed) return "";
      if (/^\*\*Works Cited\*\*/i.test(trimmed)) return `<h3>Works Cited</h3>`;
      if (/^\d+\.\s/.test(trimmed))
        return `<div class="rag-bibliography">${trimmed
          .split(/\n/)
          .map((line) => `<div>${esc(line)}</div>`)
          .join("")}</div>`;
      return `<p>${esc(trimmed).replace(/\n/g, "<br>")}</p>`;
    })
    .join("");
}

export function annotationMatches(item: Loose, query: unknown): boolean {
  const q = String(query || "")
    .trim()
    .toLocaleLowerCase();
  if (!q) return true;
  const annotation = item.annotation || {};
  return [
    item.work,
    item.record?.record_id,
    item.file?.name,
    item.store,
    annotation.note,
    annotation.quote,
    annotation.author,
    annotation.initiated_by,
    ...(annotation.tags || []),
  ].some((value) =>
    String(value || "")
      .toLocaleLowerCase()
      .includes(q),
  );
}
