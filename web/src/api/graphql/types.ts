/* Copyright 2026 Aaron John Schlosser, PhD. */
// Result shapes of the operations in ./operations. Field names keep cELF snake_case.

export interface CelfObjectType {
  type: string;
  profile: string;
  persistence: string;
  label: string;
  normative: boolean;
}

export interface CelfRelationship {
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

export interface CelfModel {
  specification_version: string;
  nodes: CelfObjectType[];
  edges: CelfRelationship[];
}

export interface ResearchObjectNode {
  id: string;
  object_type: string;
  object_id: string;
  label: string;
  summary: string;
  materialization: string;
  status: string | null;
  details: Record<string, unknown>;
}

export interface ResearchObjectEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  inverse_relation: string;
  normative: boolean;
  source_cardinality: string | null;
  target_cardinality: string | null;
  profile: string | null;
  status: string | null;
}

export interface ResearchObjectGraph {
  specification_version: string;
  root_id: string;
  hidden_assertion_count: number;
  record_state_origin: string;
  nodes: ResearchObjectNode[];
  edges: ResearchObjectEdge[];
}

export interface SimilarValidatedClaimResult {
  claim_id: string;
  claim_text: string;
  similarity: number;
  validated_by: string | null;
  validated_at: string | null;
  advisory: boolean;
  support: Array<{
    record_id: string;
    record_revision: number | null;
    relation: string | null;
    semantic: Record<string, { value: unknown; authority?: string }>;
  }>;
}

export interface OperationResults {
  CelfModel: { celf_model: CelfModel };
  RecordGraph: { record_graph: ResearchObjectGraph };
  SimilarValidatedClaims: {
    generated_claim: { claim_id: string; similar_validated_claims: SimilarValidatedClaimResult[] };
  };
}

export interface OperationVariables {
  CelfModel: Record<string, never>;
  RecordGraph: { record: Record<string, unknown>; include_assertion_history?: boolean };
  SimilarValidatedClaims: { claim_id: string; limit: number };
}
