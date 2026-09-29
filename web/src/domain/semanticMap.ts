/* Copyright 2026 Aaron John Schlosser, PhD. */

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
}

export interface SemanticMapEdge {
  id: string;
  source: string;
  target: string;
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
const MAX_TERMS_PER_RECORD = 5;

export function termList(value: unknown): string[] {
  const raw = Array.isArray(value)
    ? value
    : typeof value === "string"
      ? value.split(/[;,]/)
      : [];
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

export function slimSemanticSource(record: Record<string, unknown> | null | undefined): SemanticMapSource | null {
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
  record: 40,
  concept: 150,
  topic: 250,
  person: 340,
};

function place(id: string, kind: SemanticMapKind): MapPoint {
  const angle = ((hash(id) % 3600) / 3600) * Math.PI * 2;
  const ring = RING[kind] + (hash(`${kind}:${id}`) % 48);
  return { x: Math.cos(angle) * ring, y: Math.sin(angle) * ring };
}

function nodeId(kind: SemanticMapKind, label: string): string {
  return `${kind}:${label.toLocaleLowerCase()}`;
}

/** Co-occurring concepts, topics, and persons, plus the focused record when one is open. */
export function buildSemanticMap(sources: SemanticMapSource[], focusId = ""): SemanticMapGraph {
  const weights = new Map<string, { label: string; kind: SemanticMapKind; weight: number }>();
  const links = new Map<string, { source: string; target: string }>();

  function touch(kind: SemanticMapKind, label: string) {
    const id = nodeId(kind, label);
    const current = weights.get(id);
    if (current) current.weight += 1;
    else weights.set(id, { label, kind, weight: 1 });
    return id;
  }

  function link(left: string, right: string) {
    if (!left || !right || left === right) return;
    const [source, target] = left < right ? [left, right] : [right, left];
    links.set(`${source}|${target}`, { source, target });
  }

  for (const source of sources) {
    const ids = [
      ...source.concepts.slice(0, MAX_TERMS_PER_RECORD).map((label) => touch("concept", label)),
      ...source.topics.slice(0, MAX_TERMS_PER_RECORD).map((label) => touch("topic", label)),
      ...source.persons.slice(0, MAX_TERMS_PER_RECORD).map((label) => touch("person", label)),
    ].slice(0, MAX_TERMS_PER_RECORD);
    for (let index = 0; index < ids.length; index += 1) {
      for (let next = index + 1; next < ids.length; next += 1) link(ids[index], ids[next]);
    }
    if (focusId && source.id === focusId) {
      const recordLabel = source.work || source.id;
      const recordNode = touch("record", recordLabel);
      for (const id of ids) link(recordNode, id);
    }
  }

  const ranked = [...weights.entries()].sort(
    (left, right) => right[1].weight - left[1].weight || left[1].label.localeCompare(right[1].label),
  );
  const kept = new Set(ranked.slice(0, MAX_NODES).map(([id]) => id));
  const nodes = ranked
    .filter(([id]) => kept.has(id))
    .map(([id, meta]) => ({ id, ...meta, ...place(id, meta.kind) }));
  const edges = [...links.values()]
    .filter((edge) => kept.has(edge.source) && kept.has(edge.target))
    .map((edge) => ({ ...edge, id: `${edge.source}|${edge.target}` }));
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
  return Math.min(2.6, Math.max(0.45, scale));
}
