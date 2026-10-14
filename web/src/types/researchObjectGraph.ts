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

export type ResearchObjectMaterialization =
  | "materialized"
  | "embedded"
  | "derived_view"
  | "reference"
  | "unavailable";

export interface ResearchObjectNode {
  id: string;
  object_type: string;
  object_id: string;
  label: string;
  summary?: string;
  materialization?: ResearchObjectMaterialization | string;
  status?: string | null;
  details?: Record<string, unknown>;
}

export interface ResearchObjectEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  inverse_relation: string;
  normative: boolean;
  source_cardinality?: string | null;
  target_cardinality?: string | null;
  profile?: string | null;
  status?: string | null;
}

export interface ResearchObjectGraph {
  specification_version: string;
  root_id: string;
  nodes: ResearchObjectNode[];
  edges: ResearchObjectEdge[];
  /** Superseded / earlier-pass assertions left out of the map (still on the record). */
  hidden_assertion_count?: number;
}

export interface DerridaiModelNode {
  type: string;
  profile: string;
  persistence: string;
  label: string;
  normative: boolean;
}

export interface DerridaiModelEdge {
  id: string;
  source_type: string;
  target_type: string;
  relation: string;
  inverse_relation: string;
  source_cardinality: string;
  target_cardinality: string;
  profile: string;
  normative: boolean;
}

export interface DerridaiNormativeModel {
  specification_version: string;
  nodes: DerridaiModelNode[];
  edges: DerridaiModelEdge[];
}
