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

/**
 * Deterministic force-directed layout for the bounded semantic-map view.
 *
 * The server never sends more than a few hundred nodes, so a synchronous
 * O(n²) Fruchterman–Reingold pass is fast and, being seeded from rank order
 * rather than randomness, gives the same picture for the same view every time.
 */

export interface LayoutNode {
  id: string;
  weight?: number;
}

export interface LayoutEdge {
  source: string;
  target: string;
  weight?: number;
}

export interface LayoutPoint {
  x: number;
  y: number;
}

export interface LayoutOptions {
  width: number;
  height: number;
  iterations?: number;
  /** Node pinned at the centre (the focused entity). */
  pinned?: string;
}

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

export function layoutGraph(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  options: LayoutOptions,
): Map<string, LayoutPoint> {
  const { width, height } = options;
  const cx = width / 2;
  const cy = height / 2;
  const count = nodes.length;
  const result = new Map<string, LayoutPoint>();
  if (!count) return result;
  if (count === 1) {
    result.set(nodes[0].id, { x: cx, y: cy });
    return result;
  }

  const index = new Map(nodes.map((node, i) => [node.id, i]));
  const xs = new Float64Array(count);
  const ys = new Float64Array(count);
  const radius = Math.min(width, height) * 0.45;
  // Sunflower seeding: highest-ranked nodes start near the centre.
  nodes.forEach((node, i) => {
    const r = radius * Math.sqrt((i + 0.5) / count);
    xs[i] = cx + r * Math.cos(i * GOLDEN_ANGLE);
    ys[i] = cy + r * Math.sin(i * GOLDEN_ANGLE);
  });
  const pinned = options.pinned ? index.get(options.pinned) : undefined;
  if (pinned !== undefined) {
    xs[pinned] = cx;
    ys[pinned] = cy;
  }

  const links = edges
    .map((edge) => [index.get(edge.source), index.get(edge.target), edge.weight || 1] as const)
    .filter((link): link is readonly [number, number, number] => {
      return link[0] !== undefined && link[1] !== undefined && link[0] !== link[1];
    });
  const maxWeight = Math.max(1, ...links.map((link) => link[2]));

  const k = Math.sqrt((width * height) / count) * 1.35;
  const iterations = options.iterations ?? Math.max(60, Math.min(260, 24000 / count));
  let temperature = Math.min(width, height) / 8;
  const cooling = temperature / (iterations + 1);
  const dx = new Float64Array(count);
  const dy = new Float64Array(count);

  for (let step = 0; step < iterations; step += 1) {
    dx.fill(0);
    dy.fill(0);
    for (let i = 0; i < count; i += 1) {
      for (let j = i + 1; j < count; j += 1) {
        let ddx = xs[i] - xs[j];
        let ddy = ys[i] - ys[j];
        let dist2 = ddx * ddx + ddy * ddy;
        if (dist2 < 0.01) {
          ddx = ((i * 13 + j * 7) % 11) - 5 || 1;
          ddy = ((i * 5 + j * 3) % 11) - 5 || 1;
          dist2 = ddx * ddx + ddy * ddy;
        }
        const force = (k * k) / dist2;
        dx[i] += ddx * force;
        dy[i] += ddy * force;
        dx[j] -= ddx * force;
        dy[j] -= ddy * force;
      }
    }
    for (const [a, b, weight] of links) {
      const ddx = xs[a] - xs[b];
      const ddy = ys[a] - ys[b];
      const dist = Math.sqrt(ddx * ddx + ddy * ddy) || 0.01;
      const strength = 0.4 + 0.6 * (weight / maxWeight);
      const force = ((dist * dist) / k) * strength;
      const fx = (ddx / dist) * force;
      const fy = (ddy / dist) * force;
      dx[a] -= fx;
      dy[a] -= fy;
      dx[b] += fx;
      dy[b] += fy;
    }
    for (let i = 0; i < count; i += 1) {
      if (i === pinned) continue;
      // Gentle gravity keeps disconnected components on screen.
      dx[i] += (cx - xs[i]) * 0.02 * k;
      dy[i] += (cy - ys[i]) * 0.02 * k;
      const length = Math.sqrt(dx[i] * dx[i] + dy[i] * dy[i]) || 1;
      const move = Math.min(length, temperature);
      xs[i] += (dx[i] / length) * move;
      ys[i] += (dy[i] / length) * move;
    }
    temperature = Math.max(0.5, temperature - cooling);
  }

  // Fit into the frame with a margin so labels are not clipped.
  const margin = 48;
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (let i = 0; i < count; i += 1) {
    minX = Math.min(minX, xs[i]);
    maxX = Math.max(maxX, xs[i]);
    minY = Math.min(minY, ys[i]);
    maxY = Math.max(maxY, ys[i]);
  }
  const scale = Math.min(
    (width - margin * 2) / Math.max(1, maxX - minX),
    (height - margin * 2) / Math.max(1, maxY - minY),
    1.6,
  );
  const offsetX = cx - ((minX + maxX) / 2) * scale;
  const offsetY = cy - ((minY + maxY) / 2) * scale;
  nodes.forEach((node, i) => {
    result.set(node.id, {
      x: Math.round((xs[i] * scale + offsetX) * 10) / 10,
      y: Math.round((ys[i] * scale + offsetY) * 10) / 10,
    });
  });
  return result;
}

/** Radius from mentions, on a square-root scale so area tracks frequency. */
export function nodeRadius(mentions: number, maxMentions: number): number {
  const ratio = Math.sqrt(Math.max(0, mentions)) / Math.sqrt(Math.max(1, maxMentions));
  return Math.round((3.5 + ratio * 10) * 10) / 10;
}
