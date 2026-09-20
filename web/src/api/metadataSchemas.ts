import { apiRequest } from "./http";

export type SchemaFieldType = "text" | "number" | "boolean" | "choice" | "list";
export interface SchemaValue { value: string; definition: string }
export interface SchemaField {
  name: string; label: string; type: SchemaFieldType; group: string; values: SchemaValue[]; strict: boolean;
  instruction: string; definitions_heading: string; evidence: boolean; assess: boolean; review: boolean;
}
export interface SchemaGroup { key: string; label: string; intro: string; fields_heading: string; notes: string[]; trailer: string; footer: string }
export interface MetadataSchema { format_version: number; id: string; name: string; description: string; groups: SchemaGroup[]; fields: SchemaField[] }
export interface SchemaSummary { id: string; name: string; description: string; builtin: boolean; field_count: number; groups: string[]; hash: string }
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
  return { name: "", label: "", type: "text", group, values: [], strict: false, instruction: "", definitions_heading: "", evidence: false, assess: false, review: false };
}
