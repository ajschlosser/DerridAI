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

/** A corpus record reduced to the terms the semantic map may draw. Full text stays out. */
export interface SemanticMapSource {
  id: string;
  work: string;
  concepts: string[];
  topics: string[];
  persons: string[];
}

export type SemanticMapKind = "concept" | "topic" | "person" | "record";

export interface SemanticMapNode {
  id: string;
  label: string;
  kind: SemanticMapKind;
  x: number;
  y: number;
  weight: number;
  component: number;
}

export interface SemanticMapEdge {
  id: string;
  source: string;
  target: string;
  weight: number;
}

export interface SemanticMapGraph {
  nodes: SemanticMapNode[];
  edges: SemanticMapEdge[];
}

export interface MapPoint {
  x: number;
  y: number;
}

export const SEMANTIC_MAP_PLACEMENTS = ["sidebar", "record", "modal", "page"] as const;
export type SemanticMapPlacement = (typeof SEMANTIC_MAP_PLACEMENTS)[number];

const MAX_NODES = 64;
const MAX_TERMS_PER_RECORD = 6;
const COMPONENT_GAP = 52;

export function termList(value: unknown): string[] {
  const raw = Array.isArray(value) ? value : typeof value === "string" ? value.split(/[;,]/) : [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of raw) {
    const label = String(item ?? "").trim();
    const key = label.toLocaleLowerCase();
    if (!label || seen.has(key)) continue;
    seen.add(key);
    out.push(label);
  }
  return out;
}

export function slimSemanticSource(
  record: Record<string, unknown> | null | undefined,
): SemanticMapSource | null {
  if (!record || typeof record !== "object") return null;
  const concepts = termList(record.concepts);
  const topics = termList(record.topics);
  const persons = termList(record.persons);
  const id = String(record.record_id || record._chroma_id || "").trim();
  if (!id && !concepts.length && !topics.length && !persons.length) return null;
  return {
    id,
    work: String(record.work || record.document_title || "").trim(),
    concepts,
    topics,
    persons,
  };
}

function hash(text: string): number {
  let value = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    value ^= text.charCodeAt(index);
    value = Math.imul(value, 16777619);
  }
  return value >>> 0;
}

const RING: Record<SemanticMapKind, number> = {
  record: 24,
  concept: 104,
  topic: 136,
  person: 168,
};

function nodeId(kind: SemanticMapKind, label: string, identity = ""): string {
  return `${kind}:${kind === "record" && identity ? identity : (identity || label).toLocaleLowerCase()}`;
}

function estimatedNodeWidth(label: string): number {
  return Math.min(220, Math.max(58, label.length * 6.6 + 34));
}

function balancedTerms(
  source: SemanticMapSource,
): Array<{ kind: Exclude<SemanticMapKind, "record">; label: string }> {
  const buckets: Array<{
    kind: Exclude<SemanticMapKind, "record">;
    values: string[];
    index: number;
  }> = [
    { kind: "concept", values: source.concepts, index: 0 },
    { kind: "topic", values: source.topics, index: 0 },
    { kind: "person", values: source.persons, index: 0 },
  ];
  const out: Array<{ kind: Exclude<SemanticMapKind, "record">; label: string }> = [];
  while (
    out.length < MAX_TERMS_PER_RECORD &&
    buckets.some((bucket) => bucket.index < bucket.values.length)
  ) {
    for (const bucket of buckets) {
      if (out.length >= MAX_TERMS_PER_RECORD) break;
      const label = bucket.values[bucket.index];
      bucket.index += 1;
      if (!label) continue;
      out.push({ kind: bucket.kind, label });
    }
  }
  return out;
}

function recordLabel(source: SemanticMapSource, duplicateWorks: ReadonlySet<string>): string {
  const work = source.work.trim();
  if (!work) return source.id || "Record";
  if (!duplicateWorks.has(work.toLocaleLowerCase()) || !source.id) return work;
  const suffix = source.id.length > 8 ? source.id.slice(-8) : source.id;
  return `${work} · ${suffix}`;
}

interface LayoutEntry {
  id: string;
  kind: SemanticMapKind;
  label: string;
  weight: number;
}

interface LayoutResult {
  positions: Map<string, MapPoint>;
  components: Map<string, number>;
}

function componentBounds(
  ids: readonly string[],
  positions: ReadonlyMap<string, MapPoint>,
  labels: ReadonlyMap<string, string>,
) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const id of ids) {
    const point = positions.get(id);
    if (!point) continue;
    const halfWidth = estimatedNodeWidth(labels.get(id) || id) / 2;
    minX = Math.min(minX, point.x - halfWidth);
    maxX = Math.max(maxX, point.x + halfWidth);
    minY = Math.min(minY, point.y - 20);
    maxY = Math.max(maxY, point.y + 20);
  }
  if (!Number.isFinite(minX)) return { x: 0, y: 0, width: 1, height: 1 };
  return { x: minX, y: minY, width: Math.max(1, maxX - minX), height: Math.max(1, maxY - minY) };
}

function layoutComponent(
  entries: readonly LayoutEntry[],
  links: readonly { source: string; target: string }[],
): Map<string, MapPoint> {
  const positions = new Map<string, MapPoint>();
  const labels = new Map(entries.map((entry) => [entry.id, entry.label]));
  entries.forEach((entry) => {
    const angle = ((hash(entry.id) % 3600) / 3600) * Math.PI * 2;
    const radius = RING[entry.kind] + (hash(`radius:${entry.id}`) % 34);
    positions.set(entry.id, { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius });
  });

  for (let iteration = 0; iteration < 90; iteration += 1) {
    const delta = new Map(entries.map((entry) => [entry.id, { x: 0, y: 0 }]));
    for (let left = 0; left < entries.length; left += 1) {
      for (let right = left + 1; right < entries.length; right += 1) {
        const a = entries[left];
        const b = entries[right];
        const pa = positions.get(a.id)!;
        const pb = positions.get(b.id)!;
        let dx = pb.x - pa.x;
        let dy = pb.y - pa.y;
        let distance = Math.hypot(dx, dy);
        if (distance < 0.01) {
          const angle = (hash(`${a.id}:${b.id}`) % 360) * (Math.PI / 180);
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          distance = 1;
        }
        const minimum =
          48 +
          (estimatedNodeWidth(labels.get(a.id)!) + estimatedNodeWidth(labels.get(b.id)!)) * 0.24;
        const force =
          (distance < minimum ? (minimum - distance) * 0.18 : 720 / (distance * distance)) *
          (iteration < 45 ? 1 : 0.55);
        const ux = dx / distance;
        const uy = dy / distance;
        delta.get(a.id)!.x -= ux * force;
        delta.get(a.id)!.y -= uy * force;
        delta.get(b.id)!.x += ux * force;
        delta.get(b.id)!.y += uy * force;
      }
    }
    for (const link of links) {
      const a = positions.get(link.source);
      const b = positions.get(link.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const distance = Math.max(0.01, Math.hypot(dx, dy));
      const desired = 102;
      const force = (distance - desired) * 0.04;
      delta.get(link.source)!.x += (dx / distance) * force;
      delta.get(link.source)!.y += (dy / distance) * force;
      delta.get(link.target)!.x -= (dx / distance) * force;
      delta.get(link.target)!.y -= (dy / distance) * force;
    }
    entries.forEach((entry) => {
      const position = positions.get(entry.id)!;
      delta.get(entry.id)!.x += -position.x * 0.012;
      delta.get(entry.id)!.y += -position.y * 0.012;
      position.x += Math.max(-16, Math.min(16, delta.get(entry.id)!.x));
      position.y += Math.max(-16, Math.min(16, delta.get(entry.id)!.y));
    });
  }
  return positions;
}

/**
 * Lay out each connected component locally, then pack component bounds into
 * compact shelves. This prevents disconnected clusters from being pushed onto
 * an ever-growing ring while preserving deterministic positions.
 */
function semanticLayout(
  entries: LayoutEntry[],
  links: Array<{ source: string; target: string }>,
): LayoutResult {
  const adjacency = new Map<string, string[]>(entries.map((entry) => [entry.id, []]));
  links.forEach(({ source, target }) => {
    adjacency.get(source)?.push(target);
    adjacency.get(target)?.push(source);
  });

  const componentIds = new Map<string, number>();
  const components: string[][] = [];
  const seen = new Set<string>();
  for (const entry of entries) {
    if (seen.has(entry.id)) continue;
    const queue = [entry.id];
    const component: string[] = [];
    seen.add(entry.id);
    while (queue.length) {
      const id = queue.shift()!;
      component.push(id);
      componentIds.set(id, components.length);
      for (const next of adjacency.get(id) || []) {
        if (seen.has(next)) continue;
        seen.add(next);
        queue.push(next);
      }
    }
    components.push(component);
  }

  const entryById = new Map(entries.map((entry) => [entry.id, entry]));
  const labels = new Map(entries.map((entry) => [entry.id, entry.label]));
  const localPositions = new Map<string, MapPoint>();
  const layouts = components.map((ids, index) => {
    const idSet = new Set(ids);
    const componentEntries = ids.map((id) => entryById.get(id)!).filter(Boolean);
    const componentLinks = links.filter((link) => idSet.has(link.source) && idSet.has(link.target));
    const positions = layoutComponent(componentEntries, componentLinks);
    positions.forEach((point, id) => localPositions.set(id, point));
    const bounds = componentBounds(ids, positions, labels);
    return {
      index,
      ids,
      bounds,
      width: bounds.width + COMPONENT_GAP * 2,
      height: bounds.height + COMPONENT_GAP * 2,
    };
  });

  const totalArea = layouts.reduce((sum, item) => sum + item.width * item.height, 0);
  const targetWidth = Math.max(520, Math.sqrt(Math.max(1, totalArea) * 1.55));
  const ordered = [...layouts].sort(
    (left, right) =>
      right.width * right.height - left.width * left.height || left.index - right.index,
  );

  const offsets = new Map<number, MapPoint>();
  let cursorX = 0;
  let cursorY = 0;
  let rowHeight = 0;
  let packedWidth = 0;
  for (const item of ordered) {
    if (cursorX > 0 && cursorX + item.width > targetWidth) {
      cursorX = 0;
      cursorY += rowHeight;
      rowHeight = 0;
    }
    offsets.set(item.index, {
      x: cursorX + COMPONENT_GAP - item.bounds.x,
      y: cursorY + COMPONENT_GAP - item.bounds.y,
    });
    cursorX += item.width;
    rowHeight = Math.max(rowHeight, item.height);
    packedWidth = Math.max(packedWidth, cursorX);
  }
  const packedHeight = cursorY + rowHeight;

  const positions = new Map<string, MapPoint>();
  for (const item of layouts) {
    const offset = offsets.get(item.index) || { x: 0, y: 0 };
    for (const id of item.ids) {
      const point = localPositions.get(id) || { x: 0, y: 0 };
      positions.set(id, {
        x: point.x + offset.x - packedWidth / 2,
        y: point.y + offset.y - packedHeight / 2,
      });
    }
  }
  return { positions, components: componentIds };
}

/** Co-occurring concepts, topics, persons, and Records across the supplied works. */
export function buildSemanticMap(sources: SemanticMapSource[], focusId = ""): SemanticMapGraph {
  const weights = new Map<string, { label: string; kind: SemanticMapKind; weight: number }>();
  const links = new Map<string, { source: string; target: string; weight: number }>();

  const workCounts = new Map<string, number>();
  for (const source of sources) {
    const key = source.work.trim().toLocaleLowerCase();
    if (key) workCounts.set(key, (workCounts.get(key) || 0) + 1);
  }
  const duplicateWorks = new Set(
    [...workCounts.entries()].filter(([, count]) => count > 1).map(([work]) => work),
  );

  function touch(kind: SemanticMapKind, label: string, identity = "") {
    const id = nodeId(kind, label, identity);
    const current = weights.get(id);
    if (current) current.weight += 1;
    else weights.set(id, { label, kind, weight: 1 });
    return id;
  }

  function link(left: string, right: string) {
    if (!left || !right || left === right) return;
    const [source, target] = left < right ? [left, right] : [right, left];
    const key = `${source}|${target}`;
    const current = links.get(key);
    if (current) current.weight += 1;
    else links.set(key, { source, target, weight: 1 });
  }

  for (const source of sources) {
    const ids = balancedTerms(source).map(({ kind, label }) => touch(kind, label));
    for (let index = 0; index < ids.length; index += 1) {
      for (let next = index + 1; next < ids.length; next += 1) link(ids[index], ids[next]);
    }
    if (source.id) {
      const recordNode = touch("record", recordLabel(source, duplicateWorks), source.id);
      for (const id of ids) link(recordNode, id);
      if (focusId && source.id === focusId) {
        for (const other of sources) {
          if (other.id !== source.id && other.work === source.work) {
            link(recordNode, nodeId("record", recordLabel(other, duplicateWorks), other.id));
          }
        }
      }
    }
  }

  const ranked = [...weights.entries()].sort(
    (left, right) =>
      right[1].weight - left[1].weight || left[1].label.localeCompare(right[1].label),
  );
  const kept = new Set(ranked.slice(0, MAX_NODES).map(([id]) => id));
  const keptEdges = [...links.values()].filter(
    (edge) => kept.has(edge.source) && kept.has(edge.target),
  );
  const layout = semanticLayout(
    ranked.slice(0, MAX_NODES).map(([id, meta]) => ({ id, ...meta })),
    keptEdges,
  );
  const nodes = ranked
    .filter(([id]) => kept.has(id))
    .map(([id, meta]) => ({
      id,
      ...meta,
      ...(layout.positions.get(id) || { x: 0, y: 0 }),
      component: layout.components.get(id) || 0,
    }));
  const edges = keptEdges.map((edge) => ({ ...edge, id: `${edge.source}|${edge.target}` }));
  return { nodes, edges };
}

/** Screen-pixel drag of the map background. */
export function panBy(pan: MapPoint, delta: MapPoint): MapPoint {
  return { x: pan.x + delta.x, y: pan.y + delta.y };
}

/** Dragging a term moves it in map space, so zoom does not change how far a pixel pulls it. */
export function moveNode(point: MapPoint, delta: MapPoint, scale: number): MapPoint {
  const factor = scale > 0 ? scale : 1;
  return { x: point.x + delta.x / factor, y: point.y + delta.y / factor };
}

export function clampScale(scale: number): number {
  if (!Number.isFinite(scale)) return 1;
  return Math.min(2.6, Math.max(0.35, scale));
}
