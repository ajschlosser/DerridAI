/* Copyright 2026 Aaron John Schlosser, PhD. */

/**
 * Presentation-only contracts for relational visualizations.
 *
 * These types intentionally describe how a graph is drawn and interacted with.
 * They are not persisted domain entities and must not replace cELF, semantic
 * graph, pipeline, or other authoritative relation models.
 */

export interface RelationPoint {
  x: number;
  y: number;
}

export interface RelationSize {
  width: number;
  height: number;
}

export interface RelationBounds extends RelationPoint, RelationSize {}

export interface RelationViewportState {
  pan: RelationPoint;
  zoom: number;
}

export interface RelationViewNode<T = unknown> extends RelationPoint {
  id: string;
  draggable?: boolean;
  locked?: boolean;
  selected?: boolean;
  metadata: T;
}

export interface RelationViewEdge<T = unknown> {
  id: string;
  source: string;
  target: string;
  directed?: boolean;
  label?: string;
  metadata: T;
}

export interface RelationPositionOverride {
  id: string;
  point: RelationPoint;
}
