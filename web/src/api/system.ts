import { apiRequest } from "./http";
import type { JobSummary } from "./jobs";

export interface ProviderProfile {
  id: string;
  name: string;
  type: "ollama" | "openai";
  model?: string;
  available?: boolean;
  availability_error?: string;
  model_mode?: string;
  base_url?: string;
  max_concurrent_requests?: number;
  [key: string]: unknown;
}

export interface LanguageInfo { code: string; name: string; flag: string; content_policy_ready?: boolean }
export interface LanguageContentPolicy {
  target_language?: string;
  generation_report?: { attempts: number; removed_as_wrong_language: number; categories?: Record<string, number>; short_categories?: string[] };
  code?: string;
  status?: string;
  blocked_terms?: string[];
  contextual_terms?: Array<{
    term?: string;
    allow_title_case?: boolean;
    allow_if_surrounding?: string[];
    allow_if_before_markers?: string[];
  }>;
  generated_at?: string;
  source?: string;
  provider?: string;
  model?: string;
}
export interface ResearcherContentPolicyMirror {
  ready: boolean;
  locales: string[];
  blocked_term_hashes: string[];
  contextual: Array<{
    term_hash: string;
    allow_title_case?: boolean;
    allow_if_surrounding?: string[];
    allow_if_before_markers?: string[];
  }>;
}
export interface LanguageTranslationReport {
  status?: string;
  source_locale?: string;
  provider?: string;
  model?: string;
  completed_at?: string;
  failed_count?: number;
  fallback_count?: number;
  failed_keys?: string[];
  failures?: Array<{key?:string;reason?:string}>;
  translated_count?: number;
  key_count?: number;
}
export interface LanguageDictionary extends LanguageInfo { dictionary: Record<string, string>; translation_report?: LanguageTranslationReport }
export interface SystemDataColumn {
  name: string;
  type?: string;
  nullable?: boolean;
  default?: unknown;
  primary_key?: number;
  sensitive?: boolean;
}
export interface SystemDataOperations {
  insert: boolean;
  update: boolean;
  delete: boolean;
}
export interface SystemDataTable {
  name: string;
  columns: SystemDataColumn[];
  row_count: number;
  writable?: boolean;
  operations?: SystemDataOperations;
}
export interface SystemDataDatabase {
  name: string;
  backend: string;
  path?: string;
  size_bytes?: number;
  tables: SystemDataTable[];
}

export interface SystemMetadataExemplar {
  exemplar_id: string;
  scope_id: string;
  record_id: string;
  record_revision?: number | null;
  source_document_id?: string;
  field_name: string;
  field_value: unknown;
  kind: string;
  assertion_status?: string;
  schema_id?: string;
  schema_version?: string;
  language?: string;
  region_type?: string;
  evidence_hash?: string;
  evidence_block_ids?: string[];
  context_text?: string;
}
export interface SystemMetadataExemplarFacets {
  fields: string[];
  kinds: string[];
  languages: string[];
  scopes: string[];
  schemas: string[];
}
export interface SystemMetadataExemplarPage {
  exists: boolean;
  count: number;
  limit: number;
  offset: number;
  rows: SystemMetadataExemplar[];
  facets: SystemMetadataExemplarFacets;
}
export interface SystemChromaCollection {
  name: string;
  count: number;
  derived?: boolean;
  role?: string;
}
export interface SystemResponseCachePage {
  exists?: boolean;
  records: Array<Record<string, unknown>>;
  count?: number;
  total: number;
  limit: number;
  offset: number;
}
export interface SystemChromaCommandResult {
  valid: boolean;
  verb: "get" | "query";
  collection: string;
  options: Record<string, unknown>;
  embedding_provider?: string;
  embedding_model?: string | null;
  explanation: string;
  result?: Record<string, unknown>;
}

export interface SystemMetadataExemplarFilters {
  limit?: number;
  offset?: number;
  field?: string;
  kind?: string;
  language?: string;
  scope_id?: string;
  schema_id?: string;
  record_id?: string;
}

export const systemApi = {
  researcherProviders: () => apiRequest<{profiles: ProviderProfile[]}>("/api/system/researcher-providers"),
  setResearcherProviders: (profiles: ProviderProfile[]) => apiRequest<{profiles: ProviderProfile[]}>("/api/system/researcher-providers", {method: "PUT", body: JSON.stringify({profiles})}),
  researcherProviderStatus: (payload: Record<string, unknown>) => apiRequest<{available: boolean; models?: Array<{name: string; [key: string]: unknown}>; error?: string}>("/api/system/researcher-providers/status", {method: "POST", body: JSON.stringify(payload)}),
  researcherProviderAvailability: (id: string) => apiRequest<{available: boolean; model_available: boolean; configured_model?: string; error?: string}>(`/api/system/researcher-providers/availability`, {method: "POST", body: JSON.stringify({id})}),
  llmStatus: (payload: Record<string, unknown>) => apiRequest<{available: boolean; models?: Array<{name: string; [key: string]: unknown}>; error?: string}>("/api/llm/status", {method: "POST", body: JSON.stringify(payload)}),
  languages: () => apiRequest<{languages: LanguageInfo[]}>("/api/i18n/languages"),
  language: (code: string) => apiRequest<LanguageDictionary>(`/api/i18n/languages/${encodeURIComponent(code)}`),
  updateLanguage: (code: string, payload: Omit<LanguageDictionary, "code">) => apiRequest<LanguageDictionary>(`/api/i18n/languages/${encodeURIComponent(code)}`, {method: "PUT", body: JSON.stringify(payload)}),
  installLanguage: (payload: Record<string, unknown>) => apiRequest<JobSummary>("/api/jobs/llm-tool", {method: "POST", body: JSON.stringify({task: "language_dictionary", language: payload, label: `Languages · ${String(payload.code || "dictionary")}`, provider_profile_id: String(payload.provider_profile_id || "") || null, max_concurrent_requests: Number(payload.max_concurrent_requests || 1)})}),
  deleteLanguage: (code: string) => apiRequest<{deleted: string}>(`/api/i18n/languages/${encodeURIComponent(code)}`, {method: "DELETE"}),
  contentPolicyMirror: () => apiRequest<ResearcherContentPolicyMirror>("/api/i18n/content-policy"),
  languageContentPolicy: (code: string) => apiRequest<LanguageContentPolicy>(`/api/i18n/languages/${encodeURIComponent(code)}/content-policy`),
  updateLanguageContentPolicy: (code: string, payload: Pick<LanguageContentPolicy, "blocked_terms" | "contextual_terms">) => apiRequest<LanguageContentPolicy>(`/api/i18n/languages/${encodeURIComponent(code)}/content-policy`, {method: "PUT", body: JSON.stringify(payload)}),
  generateLanguageContentPolicy: (payload: Record<string, unknown>) => apiRequest<JobSummary>("/api/jobs/llm-tool", {method: "POST", body: JSON.stringify({task: "language_content_policy", language: payload, label: `Languages · ${String(payload.code || "policy")}`, provider_profile_id: String(payload.provider_profile_id || "") || null, max_concurrent_requests: Number(payload.max_concurrent_requests || 1)})}),
  systemData: () => apiRequest<{databases: SystemDataDatabase[]}>("/api/system/data"),
  responseCacheRecords: (limit = 25, offset = 0, query = "") => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (query.trim()) params.set("query", query.trim());
    return apiRequest<SystemResponseCachePage>(`/api/response-cache/records?${params}`);
  },
  clearResponseCache: () => apiRequest<Record<string, unknown>>("/api/stores/_response_cache", { method: "DELETE" }),
  systemChromaCollections: () => apiRequest<{collections: SystemChromaCollection[]}>("/api/system/chroma/collections"),
  validateSystemChroma: (command: string) => apiRequest<SystemChromaCommandResult>("/api/system/chroma/validate", {method: "POST", body: JSON.stringify({command})}),
  querySystemChroma: (command: string) => apiRequest<SystemChromaCommandResult>("/api/system/chroma/query", {method: "POST", body: JSON.stringify({command})}),

  systemMetadataExemplars: (filters: SystemMetadataExemplarFilters = {}) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value === undefined || value === null || String(value).trim() === "") continue;
      query.set(key, String(value));
    }
    const queryString = query.toString();
    const suffix = queryString ? `?${queryString}` : "";
    return apiRequest<SystemMetadataExemplarPage>(`/api/system/data/metadata-exemplars${suffix}`);
  },
  systemDataRows: (database: string, table: string, limit = 50, offset = 0) => apiRequest<SystemDataTable & { database: string; rows: Array<Record<string, unknown>>; offset: number; limit: number }>(`/api/system/data/${encodeURIComponent(database)}/${encodeURIComponent(table)}?limit=${limit}&offset=${offset}`),
  insertSystemDataRow: (database: string, table: string, values: Record<string, unknown>) => apiRequest<Record<string, unknown>>(`/api/system/data/${encodeURIComponent(database)}/${encodeURIComponent(table)}`, {method: "POST", body: JSON.stringify(values)}),
  updateSystemDataRow: (database: string, table: string, key: Record<string, unknown>, values: Record<string, unknown>) => apiRequest<Record<string, unknown>>(`/api/system/data/${encodeURIComponent(database)}/${encodeURIComponent(table)}`, {method: "PATCH", body: JSON.stringify({key, values})}),
  deleteSystemDataRow: (database: string, table: string, key: Record<string, unknown>) => apiRequest<Record<string, unknown>>(`/api/system/data/${encodeURIComponent(database)}/${encodeURIComponent(table)}`, {method: "DELETE", body: JSON.stringify({key})}),
  deleteSystemResponseCacheRecord: (recordId: string) => apiRequest<Record<string, unknown>>(`/api/system/data/response-cache-records/${encodeURIComponent(recordId)}`, {method: "DELETE"}),
};
