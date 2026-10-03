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
