import { apiRequest } from "./http";

export type SchemaFieldType = "text" | "number" | "boolean" | "choice" | "list";
export interface RetrievalProfile {
  enabled: boolean; scope: "same_schema" | "same_field" | "all_reviewed"; max_items: number;
  min_similarity: number; include_corrections: boolean; include_confirmed_absence: boolean;
  use_for_metadata_enrichment: boolean; use_for_response_memory: boolean; use_for_claim_memory: boolean;
}
export interface SchemaValue { value: string; definition: string }
export interface SchemaField {
  field_id: string; name: string; semantic_compatibility_id?: string | null; label: string; type: SchemaFieldType; group: string; values: SchemaValue[]; strict: boolean;
  instruction: string; definitions_heading: string; evidence: boolean; assess: boolean; review: boolean;
  retrieval_profile: RetrievalProfile;
}
export interface SchemaGroup { key: string; label: string; intro: string; fields_heading: string; notes: string[]; trailer: string; footer: string; retrieval_profile?: RetrievalProfile | null }
export interface MetadataSchema { format_version: number; schema_version?: string; id: string; name: string; description: string; groups: SchemaGroup[]; fields: SchemaField[] }
export interface SchemaSummary { id: string; name: string; description: string; schema_version?: string; builtin: boolean; field_count: number; groups: string[]; hash: string }
export interface SchemaPreview { prompt: string; answer_schema: unknown; ran: boolean; answer?: unknown; seconds?: number }

/** The three fields every schema has, in the "discourse" group. Their instructions are built in and cannot be edited. */
export const CORE_FIELDS = ["region_type", "primary_text", "discourse_role"] as const;
export const CORE_GROUP = "discourse";

const base = "/api/pdf/metadata-schemas";
export const metadataSchemasApi = {
  list: () => apiRequest<{ items: SchemaSummary[] }>(base),
  get: (id: string) => apiRequest<MetadataSchema>(`${base}/${encodeURIComponent(id)}`),
  create: (schema: MetadataSchema) => apiRequest<MetadataSchema>(base, { method: "POST", body: JSON.stringify(schema) }),
  update: (id: string, schema: MetadataSchema) => apiRequest<MetadataSchema>(`${base}/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(schema) }),
  remove: (id: string) => apiRequest<{ deleted: string }>(`${base}/${encodeURIComponent(id)}`, { method: "DELETE" }),
  exportFile: (id: string) => apiRequest<Record<string, unknown>>(`${base}/${encodeURIComponent(id)}/export`),
  importFile: (payload: unknown) => apiRequest<MetadataSchema>(`${base}/import`, { method: "POST", body: JSON.stringify(payload) }),
  preview: (payload: Record<string, unknown>) => apiRequest<SchemaPreview>(`${base}/preview`, { method: "POST", body: JSON.stringify(payload) }),
};

export function blankField(group = CORE_GROUP): SchemaField {
  return { field_id: "", name: "", label: "", type: "text", group, values: [], strict: false, instruction: "", definitions_heading: "", evidence: false, assess: false, review: false, retrieval_profile: { enabled: true, scope: "same_field", max_items: 6, min_similarity: 0, include_corrections: true, include_confirmed_absence: true, use_for_metadata_enrichment: true, use_for_response_memory: false, use_for_claim_memory: false } };
}
