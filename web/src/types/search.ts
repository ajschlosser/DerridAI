export type SearchScope = "loaded" | "database";
export type SearchLayout = "compact" | "roomy" | "cards";
export type SearchMethod = "similarity" | "mmr" | "filter";

export interface SearchStoreOption {
  name: string;
  count: number;
  filter_fields?: string[];
  schema_id?: string;
}

export interface SearchColumnOption {
  key: string;
  label: string;
}

export interface SearchFilter {
  id: string;
  field: string;
  field_label: string;
  op: string;
  op_label: string;
  value: string;
}

export interface SearchFacetValue {
  value: string;
  label: string;
  count: number;
  selected: boolean;
}

export interface SearchFacet {
  field: string;
  label: string;
  values: SearchFacetValue[];
}

export interface SearchResult {
  key: string;
  kind: "workspace" | "database";
  file_id?: string;
  file_name?: string;
  index?: number;
  collection?: string;
  chroma_id?: string;
  record_id: string;
  work: string;
  page_span: string;
  text: string;
  record: Record<string, unknown>;
  db_status?: { kind: string; label: string; title?: string };
  selected: boolean;
  evidence_selected: boolean;
  evidence_available: boolean;
  distance?: number | null;
  similarity?: number | null;
  mmr_score?: number | null;
  match_reasons: string[];
}

export interface SearchWorkspaceSnapshot {
  ready: boolean;
  is_researcher: boolean;
  scope: SearchScope;
  query: string;
  method: SearchMethod;
  fetch_k: number;
  lambda_mult: number;
  advanced_open: boolean;
  stores: SearchStoreOption[];
  active_store: string;
  has_database: boolean;
  has_loaded_records: boolean;
  total_loaded_records: number;
  results: SearchResult[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  layout: SearchLayout;
  sort: { key: string; dir: number };
  columns: SearchColumnOption[];
  available_columns: SearchColumnOption[];
  facets: SearchFacet[];
  filters: SearchFilter[];
  filter_fields: SearchColumnOption[];
  filter_suggestions: Record<string, string[]>;
  selection_count: number;
  selected_evidence_count: number;
  loading: boolean;
  search_has_run: boolean;
  capabilities: {
    can_select: boolean;
    can_review: boolean;
    can_bulk_edit: boolean;
    can_manage_database: boolean;
    can_select_evidence: boolean;
  };
}

export interface SavedSearchView {
  id: string;
  name: string;
  href: string;
  created_at: string;
  updated_at: string;
}

export interface RecentSearchEntry {
  id: string;
  query: string;
  scope: SearchScope;
  method?: SearchMethod;
  href: string;
  created_at: string;
}
