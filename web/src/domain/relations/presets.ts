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
 * Shared presentation presets for DerridAI relationship surfaces.
 *
 * The preset identifies the interaction/rendering configuration only. Domain
 * meaning remains in each adapter (pipeline edges, cELF relationships,
 * semantic graph authority, and so on).
 */

export type RelationLayoutKind = "free" | "force" | "radial" | "lanes" | "dag";
export type RelationNodeVisualKind = "chip" | "dot" | "card";
export type RelationEdgeVisualKind = "line" | "curved" | "directed";
export type RelationResizeAxis = "horizontal" | "vertical" | "both";

export interface RelationSurfacePreset {
  id:
    | "semantic-free"
    | "semantic-network"
    | "semantic-radial"
    | "provenance-lanes"
    | "pipeline-dag";
  layout: RelationLayoutKind;
  nodeVisual: RelationNodeVisualKind;
  edgeVisual: RelationEdgeVisualKind;
  minZoom: number;
  maxZoom: number;
  resizeAxis: RelationResizeAxis;
  draggableNodes: boolean;
  panByDrag: boolean;
  keyboardNudge: boolean;
  fitToContent: boolean;
}

export const RELATION_SURFACE_PRESETS = {
  semanticFree: {
    id: "semantic-free",
    layout: "free",
    nodeVisual: "chip",
    edgeVisual: "line",
    minZoom: 0.35,
    maxZoom: 2.6,
    resizeAxis: "vertical",
    draggableNodes: true,
    panByDrag: true,
    keyboardNudge: true,
    fitToContent: true,
  },
  semanticNetwork: {
    id: "semantic-network",
    layout: "force",
    nodeVisual: "dot",
    edgeVisual: "curved",
    minZoom: 0.5,
    maxZoom: 6,
    resizeAxis: "vertical",
    draggableNodes: true,
    panByDrag: true,
    keyboardNudge: true,
    fitToContent: true,
  },
  semanticRadial: {
    id: "semantic-radial",
    layout: "radial",
    nodeVisual: "dot",
    edgeVisual: "line",
    minZoom: 0.5,
    maxZoom: 4,
    resizeAxis: "vertical",
    draggableNodes: true,
    panByDrag: true,
    keyboardNudge: true,
    fitToContent: true,
  },
  provenanceLanes: {
    id: "provenance-lanes",
    layout: "lanes",
    nodeVisual: "card",
    edgeVisual: "curved",
    minZoom: 0.45,
    maxZoom: 4,
    resizeAxis: "vertical",
    draggableNodes: true,
    panByDrag: true,
    keyboardNudge: true,
    fitToContent: true,
  },
  pipelineDag: {
    id: "pipeline-dag",
    layout: "dag",
    nodeVisual: "card",
    edgeVisual: "directed",
    minZoom: 0.45,
    maxZoom: 4,
    resizeAxis: "vertical",
    draggableNodes: true,
    panByDrag: true,
    keyboardNudge: true,
    fitToContent: true,
  },
} as const satisfies Record<string, RelationSurfacePreset>;
