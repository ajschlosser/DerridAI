import type { Annotation } from "./annotations";

export type RecordAnnotationItem = Partial<Annotation> & {
  id: string;
  record_id?: string;
  field: string;
  quote: string;
  note: string;
  tags: string[];
  author: string;
  created_at?: string | null;
  removable: boolean;
  shared_annotation_id?: string | null;
};

export interface RecordHistoryItem {
  id: string;
  field_name: string;
  timestamp?: string | null;
  source: string;
  initiated_by?: string | null;
  model?: string | null;
  reason?: string | null;
}

export interface RecordPdfLink {
  pdf_file: string;
  pdf_page: number;
}

export interface RecordWorkspaceCapabilities {
  edit: boolean;
  annotate: boolean;
  evidence: boolean;
  review: boolean;
  upsert: boolean;
  llm_review: boolean;
  pdf: boolean;
  history: boolean;
  copy: boolean;
}

export interface RecordWorkspaceSnapshot {
  available: boolean;
  mode: "workspace" | "database";
  reason?: string;
  record?: Record<string, unknown>;
  record_id?: string;
  file_id?: string;
  file_name?: string | null;
  collection?: string;
  current_index?: number;
  total?: number;
  has_previous?: boolean;
  has_next?: boolean;
  find_query?: string;
  find_matches?: number;
  word_count?: number;
  character_count?: number;
  evidence_selected?: boolean;
  review_selected?: boolean;
  annotations?: RecordAnnotationItem[];
  pdf_links?: RecordPdfLink[];
  history?: RecordHistoryItem[];
  history_count?: number;
  inline_citation?: string;
  full_citation?: string;
  page_span?: string;
  capabilities?: RecordWorkspaceCapabilities;
  pdf?: {
    loaded: boolean;
    related: boolean;
    current_page?: number | null;
    current_linked?: boolean;
    title: string;
    name: string;
    loaded_pages?: number[];
  };
}
