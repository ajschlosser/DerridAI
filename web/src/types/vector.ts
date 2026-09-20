/* Copyright 2026 Aaron John Schlosser, PhD. */
export type ChromaMode = "embedded" | "http";

export interface ChromaHealth {
  available: boolean;
  mode: ChromaMode;
  path: string | null;
  host_path_hint: string | null;
  data_root: string;
  url: string | null;
  tenant: string | null;
  database: string | null;
  token_configured: boolean;
  writable: boolean;
  heartbeat_ok: boolean;
  chroma_version: string | null;
  collection_count: number | null;
  identity: string;
  error: string | null;
}

export interface ChromaConnectionUpdate {
  mode: ChromaMode;
  path?: string | null;
  url?: string | null;
  token?: string | null;
  tenant?: string | null;
  database?: string | null;
}

export interface VectorCollection {
  name: string;
  storage_name?: string;
  count: number;
  description?: string;
  embedding_provider?: string;
  embedding_model?: string | null;
  embedding_dimension?: number | null;
  distance_metric?: string;
  retrieval_mode?: string;
  language_codes?: string[];
  collection_role?: string;
  status?: string;
  protected?: boolean;
  build_id?: string;
  last_synced_at?: string | null;
  source_label?: string | null;
  source_kind?: string | null;
  source_record_count?: number;
  source_snapshot_hash?: string | null;
  text_field?: string;
  manifest_version?: number;
  app_version?: string;
  last_build_error?: string | null;
  build_history?: VectorBuildRecord[];
}

export interface VectorBuildRecord {
  build_id?: string;
  status?: string;
  created_at?: string;
  finished_at?: string;
  record_count?: number;
  embedding_dimension?: number;
}

export interface VectorWorkStat {
  work: string;
  count: number;
}

export interface VectorRecord {
  record_id?: string;
  _chroma_id?: string;
  work?: string;
  page_start?: number;
  page_end?: number;
  speaker?: string;
  text?: string;
  [key: string]: unknown;
}

export interface VectorSearchResult {
  id?: string;
  distance?: number;
  hybrid_score?: number;
  retrieval_hits?: {type: string}[];
  record: VectorRecord;
}
