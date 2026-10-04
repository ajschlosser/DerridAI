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
  const centerX = width / 2;
  const centerY = height / 2;
  const nodeCount = nodes.length;
  const positions = new Map<string, LayoutPoint>();

  if (!nodeCount) return positions;
  if (nodeCount === 1) {
    positions.set(nodes[0].id, { x: centerX, y: centerY });
    return positions;
  }

  const nodeIndexById = new Map(nodes.map((node, index) => [node.id, index]));
  const xPositions = new Float64Array(nodeCount);
  const yPositions = new Float64Array(nodeCount);

  // Seed nodes on a deterministic sunflower spiral. Rank order therefore
  // determines the initial layout instead of randomness, which keeps the
  // graph stable between renders and makes layout regressions reproducible.
  const seedRadius = Math.min(width, height) * 0.45;
  nodes.forEach((_node, index) => {
    const distanceFromCenter = seedRadius * Math.sqrt((index + 0.5) / nodeCount);
    xPositions[index] = centerX + distanceFromCenter * Math.cos(index * GOLDEN_ANGLE);
    yPositions[index] = centerY + distanceFromCenter * Math.sin(index * GOLDEN_ANGLE);
  });

  const pinnedNodeIndex = options.pinned ? nodeIndexById.get(options.pinned) : undefined;
  if (pinnedNodeIndex !== undefined) {
    xPositions[pinnedNodeIndex] = centerX;
    yPositions[pinnedNodeIndex] = centerY;
  }

  // Translate string IDs to dense indexes once. The inner force loop is hot,
  // so it should not pay Map lookup costs for every iteration.
  const indexedEdges = edges
    .map(
      (edge) =>
        [
          nodeIndexById.get(edge.source),
          nodeIndexById.get(edge.target),
          edge.weight || 1,
        ] as const,
    )
    .filter((edge): edge is readonly [number, number, number] => {
      return edge[0] !== undefined && edge[1] !== undefined && edge[0] !== edge[1];
    });
  const maximumEdgeWeight = Math.max(1, ...indexedEdges.map((edge) => edge[2]));

  const idealNodeDistance = Math.sqrt((width * height) / nodeCount) * 1.35;
  const iterations = options.iterations ?? Math.max(60, Math.min(260, 24000 / nodeCount));
  let temperature = Math.min(width, height) / 8;
  const coolingPerIteration = temperature / (iterations + 1);
  const xForces = new Float64Array(nodeCount);
  const yForces = new Float64Array(nodeCount);

  for (let iteration = 0; iteration < iterations; iteration += 1) {
    xForces.fill(0);
    yForces.fill(0);

    // Fruchterman-Reingold repulsion is pairwise. The bounded server response
    // keeps this O(n²) pass small enough to run synchronously in the browser.
    for (let sourceIndex = 0; sourceIndex < nodeCount; sourceIndex += 1) {
      for (let targetIndex = sourceIndex + 1; targetIndex < nodeCount; targetIndex += 1) {
        let deltaX = xPositions[sourceIndex] - xPositions[targetIndex];
        let deltaY = yPositions[sourceIndex] - yPositions[targetIndex];
        let distanceSquared = deltaX * deltaX + deltaY * deltaY;

        if (distanceSquared < 0.01) {
          // Give coincident nodes a deterministic nudge. Random jitter would
          // make the same graph move between renders and snapshots.
          deltaX = ((sourceIndex * 13 + targetIndex * 7) % 11) - 5 || 1;
          deltaY = ((sourceIndex * 5 + targetIndex * 3) % 11) - 5 || 1;
          distanceSquared = deltaX * deltaX + deltaY * deltaY;
        }

        const repulsiveForce = (idealNodeDistance * idealNodeDistance) / distanceSquared;
        xForces[sourceIndex] += deltaX * repulsiveForce;
        yForces[sourceIndex] += deltaY * repulsiveForce;
        xForces[targetIndex] -= deltaX * repulsiveForce;
        yForces[targetIndex] -= deltaY * repulsiveForce;
      }
    }

    for (const [sourceIndex, targetIndex, edgeWeight] of indexedEdges) {
      const deltaX = xPositions[sourceIndex] - xPositions[targetIndex];
      const deltaY = yPositions[sourceIndex] - yPositions[targetIndex];
      const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY) || 0.01;
      const normalizedStrength = 0.4 + 0.6 * (edgeWeight / maximumEdgeWeight);
      const attractiveForce = ((distance * distance) / idealNodeDistance) * normalizedStrength;
      const forceX = (deltaX / distance) * attractiveForce;
      const forceY = (deltaY / distance) * attractiveForce;

      xForces[sourceIndex] -= forceX;
      yForces[sourceIndex] -= forceY;
      xForces[targetIndex] += forceX;
      yForces[targetIndex] += forceY;
    }

    for (let nodeIndex = 0; nodeIndex < nodeCount; nodeIndex += 1) {
      if (nodeIndex === pinnedNodeIndex) continue;

      // Gentle gravity keeps disconnected components in the viewport without
      // overpowering edge attraction or pairwise repulsion.
      xForces[nodeIndex] += (centerX - xPositions[nodeIndex]) * 0.02 * idealNodeDistance;
      yForces[nodeIndex] += (centerY - yPositions[nodeIndex]) * 0.02 * idealNodeDistance;

      const displacement =
        Math.sqrt(
          xForces[nodeIndex] * xForces[nodeIndex] + yForces[nodeIndex] * yForces[nodeIndex],
        ) || 1;
      const movement = Math.min(displacement, temperature);
      xPositions[nodeIndex] += (xForces[nodeIndex] / displacement) * movement;
      yPositions[nodeIndex] += (yForces[nodeIndex] / displacement) * movement;
    }

    temperature = Math.max(0.5, temperature - coolingPerIteration);
  }

  // Fit the relaxed layout into the frame while preserving a margin for
  // labels. The upper scale cap prevents sparse graphs from becoming huge.
  const margin = 48;
  let minimumX = Infinity;
  let maximumX = -Infinity;
  let minimumY = Infinity;
  let maximumY = -Infinity;
  for (let nodeIndex = 0; nodeIndex < nodeCount; nodeIndex += 1) {
    minimumX = Math.min(minimumX, xPositions[nodeIndex]);
    maximumX = Math.max(maximumX, xPositions[nodeIndex]);
    minimumY = Math.min(minimumY, yPositions[nodeIndex]);
    maximumY = Math.max(maximumY, yPositions[nodeIndex]);
  }

  const fitScale = Math.min(
    (width - margin * 2) / Math.max(1, maximumX - minimumX),
    (height - margin * 2) / Math.max(1, maximumY - minimumY),
    1.6,
  );
  const offsetX = centerX - ((minimumX + maximumX) / 2) * fitScale;
  const offsetY = centerY - ((minimumY + maximumY) / 2) * fitScale;

  nodes.forEach((node, index) => {
    positions.set(node.id, {
      x: Math.round((xPositions[index] * fitScale + offsetX) * 10) / 10,
      y: Math.round((yPositions[index] * fitScale + offsetY) * 10) / 10,
    });
  });

  return positions;
}

/** Radius from mentions, on a square-root scale so area tracks frequency. */
export function nodeRadius(mentions: number, maxMentions: number): number {
  const ratio = Math.sqrt(Math.max(0, mentions)) / Math.sqrt(Math.max(1, maxMentions));
  return Math.round((3.5 + ratio * 10) * 10) / 10;
}
