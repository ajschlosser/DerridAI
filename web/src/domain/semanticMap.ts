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
  record: 40,
  concept: 150,
  topic: 250,
  person: 340,
};

function nodeId(kind: SemanticMapKind, label: string, identity = ""): string {
  return `${kind}:${kind === "record" && identity ? identity : (identity || label).toLocaleLowerCase()}`;
}

/**
 * Lay out the projection with a deterministic weighted spring model. Initial
 * positions and component anchors are hash-derived (never random), edge springs
 * pull co-occurring terms together, and label-aware repulsion keeps separate
 * components from occupying the same space.
 */
function semanticLayout(
  entries: Array<{ id: string; kind: SemanticMapKind; label: string; weight: number }>,
  links: Array<{ source: string; target: string }>,
): Map<string, MapPoint> {
  const positions = new Map<string, MapPoint>();
  const adjacency = new Map<string, string[]>();
  entries.forEach((entry) => {
    const angle = ((hash(entry.id) % 3600) / 3600) * Math.PI * 2;
    const radius = RING[entry.kind] + (hash(`radius:${entry.id}`) % 48);
    positions.set(entry.id, { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius });
    adjacency.set(entry.id, []);
  });
  links.forEach(({ source, target }) => {
    adjacency.get(source)?.push(target);
    adjacency.get(target)?.push(source);
  });
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
      for (const next of adjacency.get(id) || []) {
        if (!seen.has(next)) {
          seen.add(next);
          queue.push(next);
        }
      }
    }
    components.push(component);
  }
  const componentAnchors = new Map<string, MapPoint>();
  const anchorRadius = Math.max(180, components.length * 82);
  components.forEach((component, index) => {
    const angle = (index / Math.max(1, components.length)) * Math.PI * 2 - Math.PI / 2;
    const anchor = {
      x: components.length === 1 ? 0 : Math.cos(angle) * anchorRadius,
      y: components.length === 1 ? 0 : Math.sin(angle) * anchorRadius,
    };
    component.forEach((id) => componentAnchors.set(id, anchor));
  });
  const labels = new Map(entries.map((entry) => [entry.id, entry.label]));
  const edgeSet = new Set(links.map(({ source, target }) => `${source}|${target}`));
  for (let iteration = 0; iteration < 80; iteration += 1) {
    const delta = new Map<string, MapPoint>(entries.map((entry) => [entry.id, { x: 0, y: 0 }]));
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
          42 +
          (Math.max(labels.get(a.id)!.length, 8) + Math.max(labels.get(b.id)!.length, 8)) * 1.7;
        const force =
          (distance < minimum ? (minimum - distance) * 0.16 : 900 / (distance * distance)) *
          (iteration < 40 ? 1 : 0.55);
        const ux = dx / distance;
        const uy = dy / distance;
        delta.get(a.id)!.x -= ux * force;
        delta.get(a.id)!.y -= uy * force;
        delta.get(b.id)!.x += ux * force;
        delta.get(b.id)!.y += uy * force;
      }
    }
    for (const link of links) {
      const a = positions.get(link.source)!;
      const b = positions.get(link.target)!;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const distance = Math.max(0.01, Math.hypot(dx, dy));
      const desired = edgeSet.has(`${link.source}|${link.target}`) ? 108 : 160;
      const force = (distance - desired) * 0.035;
      delta.get(link.source)!.x += (dx / distance) * force;
      delta.get(link.source)!.y += (dy / distance) * force;
      delta.get(link.target)!.x -= (dx / distance) * force;
      delta.get(link.target)!.y -= (dy / distance) * force;
    }
    entries.forEach((entry) => {
      const position = positions.get(entry.id)!;
      const anchor = componentAnchors.get(entry.id)!;
      delta.get(entry.id)!.x += (anchor.x - position.x) * 0.012;
      delta.get(entry.id)!.y += (anchor.y - position.y) * 0.012;
      position.x += Math.max(-18, Math.min(18, delta.get(entry.id)!.x));
      position.y += Math.max(-18, Math.min(18, delta.get(entry.id)!.y));
    });
  }
  return positions;
}

/** Co-occurring concepts, topics, persons, and Records across the supplied works. */
export function buildSemanticMap(sources: SemanticMapSource[], focusId = ""): SemanticMapGraph {
  const weights = new Map<string, { label: string; kind: SemanticMapKind; weight: number }>();
  const links = new Map<string, { source: string; target: string }>();

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
    if (source.id) {
      const recordNode = touch("record", source.work || source.id, source.id);
      for (const id of ids) link(recordNode, id);
      if (focusId && source.id === focusId)
        for (const other of sources) {
          if (other.id !== source.id && other.work === source.work)
            link(recordNode, nodeId("record", other.work || other.id, other.id));
        }
    }
  }

  const ranked = [...weights.entries()].sort(
    (left, right) =>
      right[1].weight - left[1].weight || left[1].label.localeCompare(right[1].label),
  );
  const kept = new Set(ranked.slice(0, MAX_NODES).map(([id]) => id));
  const positions = semanticLayout(
    ranked.slice(0, MAX_NODES).map(([id, meta]) => ({ id, ...meta })),
    [...links.values()].filter((edge) => kept.has(edge.source) && kept.has(edge.target)),
  );
  const nodes = ranked
    .filter(([id]) => kept.has(id))
    .map(([id, meta]) => ({ id, ...meta, ...(positions.get(id) || { x: 0, y: 0 }) }));
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
