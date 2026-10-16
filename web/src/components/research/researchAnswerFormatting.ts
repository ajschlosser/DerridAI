/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import type { ResearchResultEvidence } from "../../types/research";

export type ResearchAnswerBlock = {
  kind: "heading" | "paragraph" | "ordered" | "unordered" | "works_cited";
  text?: string;
  items?: string[];
};

export type ResearchAnswerSegment = {
  text: string;
  evidenceIndex?: number;
  bold?: boolean;
  italic?: boolean;
};

function stripOuterStrong(value: string): string | null {
  const trimmed = value.trim();
  for (const delimiter of ["**", "__"]) {
    if (
      trimmed.length > delimiter.length * 2 &&
      trimmed.startsWith(delimiter) &&
      trimmed.endsWith(delimiter)
    ) {
      return trimmed.slice(delimiter.length, -delimiter.length).trim();
    }
  }
  return null;
}

function looksLikeHeading(value: string) {
  const text = value.trim();
  return (
    text.length > 0 &&
    text.length <= 96 &&
    text.split(/\s+/).length <= 12 &&
    !/[.!?][)"'’”\]]?$/.test(text)
  );
}

function normalizedParagraph(value: string) {
  const text = value
    .split(/\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .join(" ")
    .trim();
  return stripOuterStrong(text) ?? text;
}

function normalizedListItem(value: string) {
  const text = value.trim();
  return stripOuterStrong(text) ?? text;
}

function parseBodyBlock(value: string, worksCitedLabel: string): ResearchAnswerBlock[] {
  const block = value.trim();
  if (!block) return [];

  const lines = block
    .split(/\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return [];

  const markdownHeading = lines[0].match(/^#{1,4}\s+(.+)$/);
  if (markdownHeading) {
    const headingText = stripOuterStrong(markdownHeading[1]) ?? markdownHeading[1].trim();
    const rest = lines.slice(1).join("\n");
    return [
      { kind: "heading", text: headingText },
      ...(rest ? parseBodyBlock(rest, worksCitedLabel) : []),
    ];
  }

  const strongHeading = stripOuterStrong(lines[0]);
  if (strongHeading && looksLikeHeading(strongHeading)) {
    const rest = lines.slice(1).join("\n");
    return [
      { kind: "heading", text: strongHeading },
      ...(rest ? parseBodyBlock(rest, worksCitedLabel) : []),
    ];
  }

  if (lines.every((line) => /^\d+[.)]\s+/.test(line))) {
    return [
      {
        kind: "ordered",
        items: lines.map((line) => normalizedListItem(line.replace(/^\d+[.)]\s+/, ""))),
      },
    ];
  }

  if (lines.every((line) => /^[-*•]\s+/.test(line))) {
    return [
      {
        kind: "unordered",
        items: lines.map((line) => normalizedListItem(line.replace(/^[-*•]\s+/, ""))),
      },
    ];
  }

  return [{ kind: "paragraph", text: normalizedParagraph(block) }];
}

function escapedPattern(value: string) {
  return value.replace(/[.*+?^$()|[\]\\{}]/g, "\\$&");
}

function normalizeStrongMarkup(value: string) {
  let source = value;
  const outer = stripOuterStrong(source);
  // A whole paragraph/list item wrapped in bold is almost always generated block styling rather
  // than meaningful inline emphasis. Keep its typography stable and reserve <strong> for spans.
  if (outer != null) source = outer;

  let text = "";
  let active: { delimiter: string; start: number } | null = null;
  const boldRanges: Array<{ start: number; end: number }> = [];

  for (let index = 0; index < source.length; ) {
    const delimiter = source.startsWith("**", index)
      ? "**"
      : source.startsWith("__", index)
        ? "__"
        : "";

    if (!delimiter) {
      text += source[index];
      index += 1;
      continue;
    }

    if (!active) {
      active = { delimiter, start: text.length };
    } else if (active.delimiter === delimiter) {
      if (text.length > active.start) boldRanges.push({ start: active.start, end: text.length });
      active = null;
    }
    // Delimiters are presentation syntax, not answer content. If a model leaves one unmatched,
    // dropping it is safer than letting the rest of the answer inherit accidental emphasis.
    index += delimiter.length;
  }

  return { text, ...normalizeEmphasisMarkup(text, boldRanges) };
}

// Single-delimiter emphasis must open before a non-space and close after one, and an underscore
// pair must sit at word boundaries, so arithmetic, footnote asterisks and identifiers such as
// snake_case stay literal. Unmatched single delimiters are answer content and are kept.
const EMPHASIS_PATTERN =
  /(?<![\w*])\*(?=[^\s*])([^*\n]*?[^\s*])\*(?![\w*])|(?<![\w_])_(?=[^\s_])([^_\n]*?[^\s_])_(?![\w_])/gu;

function normalizeEmphasisMarkup(
  source: string,
  boldRanges: Array<{ start: number; end: number }>,
) {
  const removed: number[] = [];
  const rawItalic: Array<{ start: number; end: number }> = [];
  for (const match of source.matchAll(EMPHASIS_PATTERN)) {
    const start = match.index ?? 0;
    const end = start + match[0].length;
    removed.push(start, end - 1);
    rawItalic.push({ start: start + 1, end: end - 1 });
  }
  if (!removed.length) return { boldRanges, italicRanges: [] };

  // Map positions in the delimited text to positions after the delimiters are removed.
  const shift = (position: number) => position - removed.filter((index) => index < position).length;
  const remap = (ranges: Array<{ start: number; end: number }>) =>
    ranges
      .map(({ start, end }) => ({ start: shift(start), end: shift(end) }))
      .filter(({ start, end }) => end > start);
  const removedSet = new Set(removed);
  const text = [...source].filter((_, index) => !removedSet.has(index)).join("");
  return { text, boldRanges: remap(boldRanges), italicRanges: remap(rawItalic) };
}

type CitationCandidate = { marker: string; evidenceIndex: number; display: string };

function citationCandidates(evidence: ResearchResultEvidence[]): CitationCandidate[] {
  // The packet is scoped to one ResearchRun. Never guess a source when two records
  // have the same human-readable citation; only unambiguous markers are actionable.
  const byMarker = new Map<string, Omit<CitationCandidate, "marker"> | null>();
  function register(marker: string, evidenceIndex: number, display: string) {
    if (!marker) return;
    const existing = byMarker.get(marker);
    if (byMarker.has(marker)) {
      if (existing && existing.evidenceIndex !== evidenceIndex) byMarker.set(marker, null);
    } else {
      byMarker.set(marker, { evidenceIndex, display });
    }
  }

  evidence.forEach((item, evidenceIndex) => {
    const citation = String(item.inline_citation || "").trim();
    register(citation, evidenceIndex, citation);

    const id = String(item.evidence_id || "")
      .trim()
      .replace(/^\[+|\]+$/g, "");
    if (!id) return;
    // Double-bracket markers occur in saved research output. Register the longest
    // marker first so [[E1]] does not become an unlinked pair of surrounding brackets.
    register(`[[${id}]]`, evidenceIndex, citation || `[${id}]`);
    register(`[${id}]`, evidenceIndex, citation || `[${id}]`);
  });
  return [...byMarker.entries()]
    .filter((entry): entry is [string, Omit<CitationCandidate, "marker">] => entry[1] !== null)
    .map(([marker, value]) => ({ marker, ...value }))
    .sort((a, b) => b.marker.length - a.marker.length);
}

export function parseResearchAnswer(value: string, worksCitedLabel: string): ResearchAnswerBlock[] {
  const source = String(value || "")
    .replace(/\r\n?/g, "\n")
    .trim();
  if (!source) return [];

  const blocks: ResearchAnswerBlock[] = [];
  const entries: string[] = [];
  let inWorksCited = false;
  const citedHeading = /^(?:#{1,4}\s*)?(?:\*\*|__)?works\s+cited(?:\*\*|__)?\s*:?[ \t]*(.*)$/i;

  for (const raw of source.split(/\n{2,}/)) {
    const block = raw.trim();
    if (!block) continue;
    const cited = block.match(citedHeading);
    if (cited) {
      blocks.push({ kind: "heading", text: worksCitedLabel });
      if (cited[1]?.trim()) entries.push(cited[1]);
      inWorksCited = true;
      continue;
    }
    if (inWorksCited) {
      entries.push(block);
      continue;
    }
    blocks.push(...parseBodyBlock(block, worksCitedLabel));
  }
  // Everything after the heading is bibliography. Answers saved before MLA numbered
  // their entries; the numbers carry no meaning in an MLA list and are dropped.
  const items = entries
    .flatMap((entry) => entry.split(/\n/))
    .map((line) => line.trim().replace(/^\d+[.)]\s+/, ""))
    .filter(Boolean);
  if (items.length) blocks.push({ kind: "works_cited", items });
  return blocks;
}

export function segmentResearchAnswer(
  value: string,
  evidence: ResearchResultEvidence[],
): ResearchAnswerSegment[] {
  const normalized = normalizeStrongMarkup(String(value || ""));
  if (!normalized.text) return [];

  const candidates = citationCandidates(evidence);
  const citationRanges: Array<{
    start: number;
    end: number;
    evidenceIndex: number;
    display: string;
  }> = [];

  if (candidates.length) {
    const lookup = new Map(candidates.map((candidate) => [candidate.marker, candidate]));
    const pattern = new RegExp(
      candidates.map((candidate) => escapedPattern(candidate.marker)).join("|"),
      "g",
    );
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(normalized.text))) {
      const candidate = lookup.get(match[0]);
      if (!candidate) continue;
      citationRanges.push({
        start: match.index,
        end: match.index + match[0].length,
        evidenceIndex: candidate.evidenceIndex,
        display: candidate.display,
      });
    }
  }

  const cuts = new Set<number>([0, normalized.text.length]);
  [...normalized.boldRanges, ...normalized.italicRanges].forEach(({ start, end }) => {
    cuts.add(start);
    cuts.add(end);
  });
  citationRanges.forEach(({ start, end }) => {
    cuts.add(start);
    cuts.add(end);
  });
  const points = [...cuts].sort((a, b) => a - b);
  const segments: ResearchAnswerSegment[] = [];

  for (let index = 0; index < points.length - 1; index += 1) {
    const start = points[index];
    const end = points[index + 1];
    if (end <= start) continue;
    const text = normalized.text.slice(start, end);
    if (!text) continue;

    const citation = citationRanges.find((range) => start >= range.start && end <= range.end);
    const bold =
      !citation && normalized.boldRanges.some((range) => start >= range.start && end <= range.end);

    const italic =
      !citation &&
      normalized.italicRanges.some((range) => start >= range.start && end <= range.end);

    const next: ResearchAnswerSegment = citation
      ? { text, evidenceIndex: citation.evidenceIndex }
      : { text, ...(bold ? { bold: true } : {}), ...(italic ? { italic: true } : {}) };

    const previous = segments.at(-1);
    if (
      previous &&
      previous.evidenceIndex === next.evidenceIndex &&
      Boolean(previous.bold) === Boolean(next.bold) &&
      Boolean(previous.italic) === Boolean(next.italic)
    ) {
      previous.text += next.text;
    } else {
      segments.push(next);
    }
  }

  // Convert resolvable evidence markers to the actual inline citation. Preserve
  // unresolved markers as ordinary text; a bibliographic string without a unique
  // packet binding must never look like a verified source link.
  for (const segment of segments) {
    if (segment.evidenceIndex == null) continue;
    const marker = citationRanges.find(
      (range) =>
        range.evidenceIndex === segment.evidenceIndex &&
        normalized.text.slice(range.start, range.end) === segment.text,
    );
    if (marker) segment.text = marker.display;
  }
  return segments;
}

/**
 * Number each bound source by its first citation in the answer's prose (not its
 * Works Cited), so the reader sees short markers while the evidence ID stays the
 * run's identity. Returns evidence index -> display number.
 */
export function citationNumbers(
  blocks: ResearchAnswerBlock[],
  evidence: ResearchResultEvidence[],
): Map<number, number> {
  const numbers = new Map<number, number>();
  for (const block of blocks) {
    if (block.kind === "works_cited") continue;
    for (const text of block.items ?? [block.text || ""]) {
      for (const segment of segmentResearchAnswer(text, evidence)) {
        if (segment.evidenceIndex != null && !numbers.has(segment.evidenceIndex)) {
          numbers.set(segment.evidenceIndex, numbers.size + 1);
        }
      }
    }
  }
  return numbers;
}

/**
 * Drop the parentheses and separators that wrapped a group made only of bound
 * citations ("writing (A; B)." -> "writing[1][2]."), since numbered markers replace
 * them. A parenthesis holding any other text is left as written.
 */
export function compactCitationGroups(segments: ResearchAnswerSegment[]): ResearchAnswerSegment[] {
  const out = segments.map((segment) => ({ ...segment }));
  const isCitation = (segment?: ResearchAnswerSegment) => segment?.evidenceIndex != null;
  const plain = (segment?: ResearchAnswerSegment) =>
    segment != null && !isCitation(segment) && !segment.bold && !segment.italic;
  for (let start = 0; start < out.length; start += 1) {
    if (!isCitation(out[start]) || !plain(out[start - 1]) || !/\(\s*$/.test(out[start - 1].text)) {
      continue;
    }
    let end = start;
    while (
      isCitation(out[end + 2]) &&
      plain(out[end + 1]) &&
      /^\s*[;,]\s*$/.test(out[end + 1].text)
    ) {
      end += 2;
    }
    const after = out[end + 1];
    if (!plain(after) || !/^\s*\)/.test(after.text)) continue;
    out[start - 1].text = out[start - 1].text.replace(/\s*\(\s*$/, "");
    after.text = after.text.replace(/^\s*\)/, "");
    for (let index = start + 1; index < end; index += 2) out[index].text = "";
    start = end;
  }
  return out.filter((segment) => segment.text !== "" || isCitation(segment));
}
