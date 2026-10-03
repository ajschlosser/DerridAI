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

import type { RelationBounds, RelationPoint, RelationSize, RelationViewportState } from "./types";

export const DEFAULT_RELATION_MIN_ZOOM = 0.45;
export const DEFAULT_RELATION_MAX_ZOOM = 6;

export function clampRelationZoom(
  value: number,
  min = DEFAULT_RELATION_MIN_ZOOM,
  max = DEFAULT_RELATION_MAX_ZOOM,
): number {
  if (!Number.isFinite(value)) return 1;
  const lower = Math.min(min, max);
  const upper = Math.max(min, max);
  return Math.min(upper, Math.max(lower, value));
}

export function panRelationViewport(pan: RelationPoint, delta: RelationPoint): RelationPoint {
  return { x: pan.x + delta.x, y: pan.y + delta.y };
}

export function screenDeltaToGraph(delta: RelationPoint, zoom: number): RelationPoint {
  const scale = Number.isFinite(zoom) && zoom > 0 ? zoom : 1;
  return { x: delta.x / scale, y: delta.y / scale };
}

export function moveRelationPoint(
  point: RelationPoint,
  screenDelta: RelationPoint,
  zoom: number,
): RelationPoint {
  const delta = screenDeltaToGraph(screenDelta, zoom);
  return { x: point.x + delta.x, y: point.y + delta.y };
}

/**
 * Convert graph coordinates to screen coordinates for the shared viewport
 * convention: screen = graph * zoom + pan.
 */
export function relationGraphToScreen(
  point: RelationPoint,
  viewport: RelationViewportState,
): RelationPoint {
  return {
    x: point.x * viewport.zoom + viewport.pan.x,
    y: point.y * viewport.zoom + viewport.pan.y,
  };
}

export function relationScreenToGraph(
  point: RelationPoint,
  viewport: RelationViewportState,
): RelationPoint {
  const zoom = Number.isFinite(viewport.zoom) && viewport.zoom > 0 ? viewport.zoom : 1;
  return {
    x: (point.x - viewport.pan.x) / zoom,
    y: (point.y - viewport.pan.y) / zoom,
  };
}

/**
 * Return a viewport state that keeps the same graph-space point underneath a
 * screen-space zoom anchor.
 */
export function zoomRelationViewportAt(
  viewport: RelationViewportState,
  nextZoom: number,
  anchor: RelationPoint,
  min = DEFAULT_RELATION_MIN_ZOOM,
  max = DEFAULT_RELATION_MAX_ZOOM,
): RelationViewportState {
  const zoom = clampRelationZoom(nextZoom, min, max);
  const graphAnchor = relationScreenToGraph(anchor, viewport);
  return {
    zoom,
    pan: {
      x: anchor.x - graphAnchor.x * zoom,
      y: anchor.y - graphAnchor.y * zoom,
    },
  };
}

export function relationBoundsForPoints(
  points: readonly RelationPoint[],
  padding = 0,
): RelationBounds | null {
  if (!points.length) return null;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const point of points) {
    if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) continue;
    minX = Math.min(minX, point.x);
    minY = Math.min(minY, point.y);
    maxX = Math.max(maxX, point.x);
    maxY = Math.max(maxY, point.y);
  }
  if (!Number.isFinite(minX) || !Number.isFinite(minY)) return null;
  const inset = Math.max(0, padding);
  return {
    x: minX - inset,
    y: minY - inset,
    width: Math.max(0, maxX - minX) + inset * 2,
    height: Math.max(0, maxY - minY) + inset * 2,
  };
}

export function fitRelationBounds(
  bounds: RelationBounds,
  viewportSize: RelationSize,
  options: {
    padding?: number;
    minZoom?: number;
    maxZoom?: number;
  } = {},
): RelationViewportState {
  const padding = Math.max(0, options.padding ?? 32);
  const availableWidth = Math.max(1, viewportSize.width - padding * 2);
  const availableHeight = Math.max(1, viewportSize.height - padding * 2);
  const contentWidth = Math.max(1, bounds.width);
  const contentHeight = Math.max(1, bounds.height);
  const zoom = clampRelationZoom(
    Math.min(availableWidth / contentWidth, availableHeight / contentHeight),
    options.minZoom,
    options.maxZoom,
  );
  const centerX = bounds.x + bounds.width / 2;
  const centerY = bounds.y + bounds.height / 2;
  return {
    zoom,
    pan: {
      x: viewportSize.width / 2 - centerX * zoom,
      y: viewportSize.height / 2 - centerY * zoom,
    },
  };
}
