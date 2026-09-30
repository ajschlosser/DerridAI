import { apiRequest } from "./http";

export type SchemaFieldType = "text" | "number" | "boolean" | "choice" | "list";
export type SchemaFieldRole = "scholarly" | "structural" | "document" | "operational";
export type SchemaReviewVisibility = "primary" | "details" | "hidden";
/** Where a value lives: on each record, or once for the whole corpus. */
export type SchemaFieldScope = "record" | "corpus";
export type DocumentRequirement = "evidence" | "publication";
export interface RetrievalProfile {
  enabled: boolean;
  max_items: number;
  min_similarity: number;
  include_corrections: boolean;
  include_confirmed_absence: boolean;
  /** Separate quota for reviewed corrections. */
  max_corrections?: number;
  /** Stable field identities a precedent's reviewed value should agree on. */
  match_field_ids?: string[];
}
/** When differently written values count as the same semantic value. Stored values are never rewritten. */
export type EquivalenceMode = "exact" | "text" | "entity_name" | "lexical_phrase" | "controlled";
export interface EquivalenceProfile {
  mode: EquivalenceMode;
  collection_semantics?: "set" | "ordered";
  identity_kind?: string | null;
}
export interface SchemaValue {
  value: string;
  definition: string;
}
export interface SchemaField {
  field_id: string;
  name: string;
  semantic_compatibility_id?: string | null;
  label: string;
  type: SchemaFieldType;
  group: string;
  role?: SchemaFieldRole;
  review_visibility?: SchemaReviewVisibility;
  /** "corpus" values are filled in once before segmentation and inherited by every record. */
  scope?: SchemaFieldScope;
  values: SchemaValue[];
  strict: boolean;
  instruction: string;
  definitions_heading: string;
  evidence: boolean;
  assess: boolean;
  review: boolean;
  retrieval_profile: RetrievalProfile;
  /** Unset: DerridAI's policy for the field's semantic identity, then its type. */
  equivalence_profile?: EquivalenceProfile | null;
  pos_tags: string[];
  ner_tags: string[];
}
export interface SchemaGroup {
  key: string;
  label: string;
  intro: string;
  fields_heading: string;
  notes: string[];
  trailer: string;
  footer: string;
  retrieval_profile?: RetrievalProfile | null;
}
/** A schema's policy for one DerridAI-owned bibliographic field (title, document_author, …). */
export interface DocumentFieldPolicy {
  name: string;
  required_for: DocumentRequirement[];
}
export interface MetadataSchema {
  format_version: number;
  schema_version?: string;
  id: string;
  name: string;
  description: string;
  groups: SchemaGroup[];
  fields: SchemaField[];
  /** One policy per document field, in DerridAI's canonical order; the server fills any that are missing. */
  document_fields?: DocumentFieldPolicy[];
}
export interface SchemaSummary {
  id: string;
  name: string;
  description: string;
  schema_version?: string;
  builtin: boolean;
  field_count: number;
  groups: string[];
  hash: string;
}
export interface SchemaPreview {
  prompt: string;
  answer_schema: unknown;
  ran: boolean;
  answer?: unknown;
  seconds?: number;
}

/** The three fields every schema has, in the "discourse" group. Their instructions are built in and cannot be edited. */
export const CORE_FIELDS = ["region_type", "primary_text", "discourse_role"] as const;
export const CORE_GROUP = "discourse";

/** DerridAI-owned bibliographic fields, in the server's canonical order (metadata_schema.DOCUMENT_FIELDS). */
export const DOCUMENT_FIELD_NAMES = [
  "title",
  "short_title",
  "original_title",
  "document_author",
  "translator",
  "publisher",
  "publication_place",
  "publication_year",
  "edition",
  "isbn",
  "language",
  "original_language",
  "document_is_translation",
  "document_type",
] as const;
const DEFAULT_REQUIRED = new Set(["title", "document_author"]);

/** The server's default policies (metadata_schema.default_document_fields). */
export function defaultDocumentFields(): DocumentFieldPolicy[] {
  return DOCUMENT_FIELD_NAMES.map((name) => ({
    name,
    required_for: DEFAULT_REQUIRED.has(name) ? ["evidence", "publication"] : [],
  }));
}

/** One policy per document field in canonical order, keeping the given ones (as the server does). */
export function completeDocumentFields(given: DocumentFieldPolicy[] = []): DocumentFieldPolicy[] {
  const byName = new Map(given.map((p) => [p.name, p]));
  return defaultDocumentFields().map((p) => byName.get(p.name) ?? p);
}

const base = "/api/pdf/metadata-schemas";
export const metadataSchemasApi = {
  list: () => apiRequest<{ items: SchemaSummary[] }>(base),
  get: (id: string) => apiRequest<MetadataSchema>(`${base}/${encodeURIComponent(id)}`),
  create: (schema: MetadataSchema) =>
    apiRequest<MetadataSchema>(base, { method: "POST", body: JSON.stringify(schema) }),
  update: (id: string, schema: MetadataSchema) =>
    apiRequest<MetadataSchema>(`${base}/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(schema),
    }),
  remove: (id: string) =>
    apiRequest<{ deleted: string }>(`${base}/${encodeURIComponent(id)}`, { method: "DELETE" }),
  exportFile: (id: string) =>
    apiRequest<Record<string, unknown>>(`${base}/${encodeURIComponent(id)}/export`),
  importFile: (payload: unknown) =>
    apiRequest<MetadataSchema>(`${base}/import`, { method: "POST", body: JSON.stringify(payload) }),
  preview: (payload: Record<string, unknown>) =>
    apiRequest<SchemaPreview>(`${base}/preview`, { method: "POST", body: JSON.stringify(payload) }),
};

export function blankField(group = CORE_GROUP): SchemaField {
  return {
    field_id: "",
    name: "",
    label: "",
    type: "text",
    group,
    role: "scholarly",
    review_visibility: "primary",
    scope: "record",
    values: [],
    strict: false,
    instruction: "",
    definitions_heading: "",
    evidence: false,
    assess: false,
    review: false,
    pos_tags: [],
    ner_tags: [],
    retrieval_profile: {
      enabled: true,
      max_items: 6,
      min_similarity: 0,
      include_corrections: true,
      include_confirmed_absence: true,
      max_corrections: 2,
      match_field_ids: [],
    },
  };
}
