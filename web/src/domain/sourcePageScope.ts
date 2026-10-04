/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

export interface PageSelectionParseResult {
  pages: number[];
  error: string;
}

/**
 * Parse reviewer-entered source-page selections such as "1-12, 17, 21-35".
 *
 * The empty string means "all pages". The parser is deliberately strict:
 * malformed/reversed/out-of-range tokens are rejected instead of silently
 * changing the documentary scope of a build.
 */
export function parseSourcePageSelection(
  value: string,
  pageCount: number,
): PageSelectionParseResult {
  const raw = value.trim();
  if (!raw) return { pages: [], error: "" };
  if (!Number.isInteger(pageCount) || pageCount < 1) {
    return { pages: [], error: "This source does not expose selectable pages." };
  }

  const selected = new Set<number>();
  const tokens = raw.split(",").map((item) => item.trim());
  if (tokens.some((token) => !token)) {
    return { pages: [], error: "Page selections cannot contain empty entries." };
  }
  for (const token of tokens) {
    const match = token.match(/^(\d+)\s*(?:[-–]\s*(\d+))?$/);
    if (!match) return { pages: [], error: `Invalid page selection: "${token}".` };

    const start = Number(match[1]);
    const end = Number(match[2] || match[1]);
    if (start < 1 || end < 1 || start > end) {
      return { pages: [], error: `Invalid page range: "${token}".` };
    }
    if (end > pageCount) {
      return { pages: [], error: `Page ${end} is outside this source (1–${pageCount}).` };
    }
    for (let page = start; page <= end; page += 1) selected.add(page);
  }
  return { pages: [...selected].sort((a, b) => a - b), error: "" };
}

/** Compact normalized display form used when restoring a saved selection. */
export function formatSourcePageSelection(pages: number[]): string {
  const values = [...new Set(pages.filter((page) => Number.isInteger(page) && page > 0))].sort(
    (a, b) => a - b,
  );
  if (!values.length) return "";

  const ranges: string[] = [];
  let start = values[0];
  let previous = values[0];
  for (const page of values.slice(1)) {
    if (page === previous + 1) {
      previous = page;
      continue;
    }
    ranges.push(start === previous ? String(start) : `${start}-${previous}`);
    start = previous = page;
  }
  ranges.push(start === previous ? String(start) : `${start}-${previous}`);
  return ranges.join(", ");
}
