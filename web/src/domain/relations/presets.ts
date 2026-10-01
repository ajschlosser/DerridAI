/* Copyright 2026 Aaron John Schlosser, PhD. */

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
    minZoom: 0.22,
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
