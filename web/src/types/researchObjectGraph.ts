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
