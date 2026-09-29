import type { ResearchResultEvidence } from "../../types/research";

export type ResearchAnswerBlock = {
  kind: "heading" | "paragraph" | "ordered" | "unordered";
  text?: string;
  items?: string[];
};

export type ResearchAnswerSegment = {
  text: string;
  evidenceIndex?: number;
  bold?: boolean;
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
    text.split(/\\s+/).length <= 12 &&
    !/[.!?][)"'’”\\]]?$/.test(text)
  );
}

function normalizedParagraph(value: string) {
  const text = value
    .split(/\\n/)
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
    .split(/\\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return [];

  const markdownHeading = lines[0].match(/^#{1,4}\\s+(.+)$/);
  if (markdownHeading) {
    const headingText = stripOuterStrong(markdownHeading[1]) ?? markdownHeading[1].trim();
    const rest = lines.slice(1).join("\\n");
    return [
      { kind: "heading", text: headingText },
      ...(rest ? parseBodyBlock(rest, worksCitedLabel) : []),
    ];
  }

  const strongHeading = stripOuterStrong(lines[0]);
  if (strongHeading && looksLikeHeading(strongHeading)) {
    const rest = lines.slice(1).join("\\n");
    return [
      { kind: "heading", text: strongHeading },
      ...(rest ? parseBodyBlock(rest, worksCitedLabel) : []),
    ];
  }

  if (lines.every((line) => /^\\d+[.)]\\s+/.test(line))) {
    return [
      {
        kind: "ordered",
        items: lines.map((line) => normalizedListItem(line.replace(/^\\d+[.)]\\s+/, ""))),
      },
    ];
  }

  if (lines.every((line) => /^[-*•]\\s+/.test(line))) {
    return [
      {
        kind: "unordered",
        items: lines.map((line) => normalizedListItem(line.replace(/^[-*•]\\s+/, ""))),
      },
    ];
  }

  return [{ kind: "paragraph", text: normalizedParagraph(block) }];
}

function escapedPattern(value: string) {
  return value.replace(/[.*+?^$()|[\\]\\\\{}]/g, "\\\\$&");
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

  return { text, boldRanges };
}

function citationCandidates(evidence: ResearchResultEvidence[]) {
  const byMarker = new Map<string, number>();
  evidence.forEach((item, index) => {
    const citation = String(item.inline_citation || "").trim();
    if (citation && !byMarker.has(citation)) byMarker.set(citation, index);

    const id = String(item.evidence_id || "").trim();
    if (id) {
      const marker = id.startsWith("[") && id.endsWith("]") ? id : "[" + id + "]";
      if (!byMarker.has(marker)) byMarker.set(marker, index);
    }
  });
  return [...byMarker.entries()]
    .map(([marker, evidenceIndex]) => ({ marker, evidenceIndex }))
    .sort((a, b) => b.marker.length - a.marker.length);
}

export function parseResearchAnswer(
  value: string,
  worksCitedLabel: string,
): ResearchAnswerBlock[] {
  const source = String(value || "")
    .replace(/\\r\\n?/g, "\\n")
    .trim();
  if (!source) return [];

  const blocks: ResearchAnswerBlock[] = [];
  const citedHeading =
    /^(?:#{1,4}\\s*)?(?:\\*\\*|__)?works\\s+cited(?:\\*\\*|__)?\\s*:?[ \\t]*(.*)$/i;

  for (const raw of source.split(/\\n{2,}/)) {
    const block = raw.trim();
    if (!block) continue;
    const cited = block.match(citedHeading);
    if (cited) {
      blocks.push({ kind: "heading", text: worksCitedLabel });
      if (cited[1]?.trim()) blocks.push(...parseBodyBlock(cited[1], worksCitedLabel));
      continue;
    }
    blocks.push(...parseBodyBlock(block, worksCitedLabel));
  }
  return blocks;
}

export function segmentResearchAnswer(
  value: string,
  evidence: ResearchResultEvidence[],
): ResearchAnswerSegment[] {
  const normalized = normalizeStrongMarkup(String(value || ""));
  if (!normalized.text) return [];

  const candidates = citationCandidates(evidence);
  const citationRanges: Array<{ start: number; end: number; evidenceIndex: number }> = [];

  if (candidates.length) {
    const lookup = new Map(candidates.map((candidate) => [candidate.marker, candidate.evidenceIndex]));
    const pattern = new RegExp(
      candidates.map((candidate) => escapedPattern(candidate.marker)).join("|"),
      "g",
    );
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(normalized.text))) {
      const evidenceIndex = lookup.get(match[0]);
      if (evidenceIndex == null) continue;
      citationRanges.push({
        start: match.index,
        end: match.index + match[0].length,
        evidenceIndex,
      });
    }
  }

  const cuts = new Set<number>([0, normalized.text.length]);
  normalized.boldRanges.forEach(({ start, end }) => {
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
      !citation &&
      normalized.boldRanges.some((range) => start >= range.start && end <= range.end);

    const next: ResearchAnswerSegment = citation
      ? { text, evidenceIndex: citation.evidenceIndex }
      : bold
        ? { text, bold: true }
        : { text };

    const previous = segments.at(-1);
    if (
      previous &&
      previous.evidenceIndex == null &&
      next.evidenceIndex == null &&
      Boolean(previous.bold) === Boolean(next.bold)
    ) {
      previous.text += next.text;
    } else {
      segments.push(next);
    }
  }

  return segments;
}
