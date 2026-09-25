/* Copyright 2026 Aaron John Schlosser, PhD. */
import { apiRequest } from "./http";

export interface MetadataMemoryEntry {
  id: string;
  memory_type: "evidence_bound";
  kind: string;
  field: string;
  value: unknown;
  rejected_value?: unknown;
  authority?: string;
  review_method?: string;
  record_id: string;
  record_revision?: number | string;
  build_id?: string;
  source_document_id?: string;
  schema_id?: string;
  schema_version?: string;
  language?: string;
  region_type?: string;
  page_start?: number | string;
  page_end?: number | string;
  reviewed_at?: string;
  evidence_bound: boolean;
  evidence_hash?: string;
  evidence_block_ids: string[];
  evidence_text?: string;
  context_text?: string;
  source_current?: boolean;
  evidence_current?: boolean;
}

export interface MetadataMemoryPayload {
  items: MetadataMemoryEntry[];
  total: number;
  offset: number;
  limit: number;
  summary: {
    entries: number;
    evidence_bound: number;
    corrections: number;
    fields: number;
    backends: number;
  };
  facets: {
    fields: string[];
    kinds: string[];
    languages: string[];
    builds: string[];
  };
  derived: boolean;
  authoritative_source: string;
  available: boolean;
  error?: string;
}

export const metadataMemoryApi = {
  list: (
    filters: {
      limit?: number;
      offset?: number;
      field?: string;
      kind?: string;
      build_id?: string;
      language?: string;
      q?: string;
    } = {},
  ) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        params.set(key, String(value));
      }
    }
    const query = params.toString();
    return apiRequest<MetadataMemoryPayload>(
      `/api/system/metadata-memory${query ? `?${query}` : ""}`,
    );
  },
};
