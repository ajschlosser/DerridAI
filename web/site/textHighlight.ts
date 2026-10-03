/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 */

export interface HighlightSegment {
  text: string;
  highlighted: boolean;
}

const TERM_PATTERN = /[\p{L}\p{N}’'_-]+/gu;

export function queryTerms(query: string, locale: string): string[] {
  return [
    ...new Set(
      String(query || "")
        .toLocaleLowerCase(locale)
        .match(TERM_PATTERN) ?? [],
    ),
  ];
}

export function matchRanges(text: string, query: string, locale: string): Array<[number, number]> {
  const terms = new Set(queryTerms(query, locale));
  if (!terms.size) return [];
  const ranges: Array<[number, number]> = [];

  for (const match of text.matchAll(TERM_PATTERN)) {
    if (terms.has(match[0].toLocaleLowerCase(locale))) {
      ranges.push([match.index, match.index + match[0].length]);
    }
  }

  const phrase = String(query || "").trim().toLocaleLowerCase(locale);
  const folded = text.toLocaleLowerCase(locale);
  if (terms.size > 1 && folded.length === text.length) {
    for (let at = folded.indexOf(phrase); phrase && at !== -1; at = folded.indexOf(phrase, at + 1)) {
      ranges.push([at, at + phrase.length]);
    }
  }

  ranges.sort((left, right) => left[0] - right[0] || right[1] - left[1]);
  const merged: Array<[number, number]> = [];
  for (const range of ranges) {
    const last = merged.at(-1);
    if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]);
    else merged.push([...range]);
  }
  return merged;
}

export function highlightSegments(
  text: string,
  query: string,
  locale: string,
): HighlightSegment[] {
  const segments: HighlightSegment[] = [];
  let from = 0;
  for (const [start, end] of matchRanges(text, query, locale)) {
    if (start > from) segments.push({ text: text.slice(from, start), highlighted: false });
    segments.push({ text: text.slice(start, end), highlighted: true });
    from = end;
  }
  if (from < text.length) segments.push({ text: text.slice(from), highlighted: false });
  if (!segments.length && text) segments.push({ text, highlighted: false });
  return segments;
}

export function snippetText(text: string, query: string, locale: string, limit = 640): string {
  if (text.length <= limit) return text;
  const first = matchRanges(text, query, locale)[0];
  if (!first || first[1] <= limit - 40) return text.slice(0, limit);
  const start = Math.max(text.lastIndexOf(" ", Math.max(first[0] - 200, 0)), 0);
  return `${start ? "…" : ""}${text.slice(start, start + limit).trimStart()}`;
}
