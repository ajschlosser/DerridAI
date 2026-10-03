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

/** An annotation span over a Record's text (see RecordSemanticMention). */
export interface TextSpan {
  start: number;
  end: number;
  layer: string;
}

export interface TextSegment<T extends TextSpan> {
  text: string;
  start: number;
  mention: T | null;
}

/**
 * Split text into plain runs and annotated runs for display.
 *
 * Only spans whose layer is shown take part. Spans can overlap (a named entity inside a quotation, a noun inside a
 * named entity); the earliest-starting span wins, the longer one on a tie, and a span overlapping one already placed
 * is left out of the rendering. The segments always concatenate back to exactly the input text.
 */
export function segmentText<T extends TextSpan>(
  text: string,
  spans: readonly T[],
  shownLayers: ReadonlySet<string>,
): TextSegment<T>[] {
  const ordered = spans
    .filter(
      (span) =>
        shownLayers.has(span.layer) &&
        span.start >= 0 &&
        span.end > span.start &&
        span.end <= text.length,
    )
    .slice()
    .sort((left, right) => left.start - right.start || right.end - left.end);
  const segments: TextSegment<T>[] = [];
  let cursor = 0;
  for (const span of ordered) {
    if (span.start < cursor) continue;
    if (span.start > cursor)
      segments.push({ text: text.slice(cursor, span.start), start: cursor, mention: null });
    segments.push({ text: text.slice(span.start, span.end), start: span.start, mention: span });
    cursor = span.end;
  }
  if (cursor < text.length)
    segments.push({ text: text.slice(cursor), start: cursor, mention: null });
  return segments;
}

export interface Point {
  x: number;
  y: number;
}

/**
 * Place a focus node at the centre, its immediate nodes on an inner ring, and further nodes on an outer ring.
 *
 * Deterministic for the same input so a node does not jump around when the reviewer walks back to it. Rings start at
 * the top and run clockwise; an outer node is drawn next to the inner node it is attached to when one is given.
 */
export function radialLayout(
  centerId: string,
  inner: readonly string[],
  outer: readonly string[],
  size: { width: number; height: number },
  attachedTo: ReadonlyMap<string, string> = new Map(),
): Map<string, Point> {
  const cx = size.width / 2;
  const cy = size.height / 2;
  const reach = Math.min(size.width, size.height) / 2;
  const innerRadius = outer.length ? reach * 0.5 : reach * 0.72;
  const outerRadius = reach * 0.88;
  const positions = new Map<string, Point>();
  const polar = (radius: number, angle: number): Point => ({
    x: Math.round((cx + radius * Math.cos(angle)) * 10) / 10,
    y: Math.round((cy + radius * Math.sin(angle)) * 10) / 10,
  });
  positions.set(centerId, { x: cx, y: cy });
  const innerAngles = new Map<string, number>();
  inner.forEach((id, index) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * index) / Math.max(1, inner.length);
    innerAngles.set(id, angle);
    positions.set(id, polar(innerRadius, angle));
  });
  const slots = outer.map(
    (_, index) => -Math.PI / 2 + (2 * Math.PI * index) / Math.max(1, outer.length),
  );
  const free = new Set(slots.map((_, index) => index));
  const nearestSlot = (angle: number) => {
    let best = -1;
    let bestDistance = Infinity;
    for (const index of free) {
      const raw = Math.abs(slots[index] - angle) % (2 * Math.PI);
      const distance = Math.min(raw, 2 * Math.PI - raw);
      if (distance < bestDistance) {
        best = index;
        bestDistance = distance;
      }
    }
    return best;
  };
  const anchored = outer.filter((id) => innerAngles.has(attachedTo.get(id) || ""));
  const loose = outer.filter((id) => !innerAngles.has(attachedTo.get(id) || ""));
  for (const id of [...anchored, ...loose]) {
    const anchor = innerAngles.get(attachedTo.get(id) || "");
    const index = anchor === undefined ? Math.min(...free) : nearestSlot(anchor);
    free.delete(index);
    positions.set(id, polar(outerRadius, slots[index]));
  }
  return positions;
}

/** Visual tone for an entity type; unknown types read as a generic entity. */
export function nodeTone(type: string): "person" | "concept" | "work" | "term" | "entity" {
  if (type === "person" || type === "character") return "person";
  if (type === "concept" || type === "topic") return "concept";
  if (type === "work") return "work";
  if (type === "term") return "term";
  return "entity";
}

export function relationLabel(edge: { predicate?: string }): string {
  return String(edge.predicate || "").replaceAll("_", " ");
}
