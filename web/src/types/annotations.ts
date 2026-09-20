// Copyright 2026 Aaron John Schlosser, PhD.

export interface AnnotationWorkspaceItem {
  id: string;
  record_id: string;
  work: string;
  field: string;
  quote: string;
  note: string;
  tags: string[];
  author: string;
  source: string;
  created_at: string | null;
  server: boolean;
  removable: boolean;
  local_file_id: string | null;
  local_index: number | null;
  local_annotation_index: number | null;
  shared_annotation_id: string | null;
}

export interface AnnotationWorkspaceGroup {
  work: string;
  annotations: AnnotationWorkspaceItem[];
  records: number;
}

export interface AnnotationsWorkspaceSnapshot {
  query: string;
  view: "works" | "recent";
  annotations: AnnotationWorkspaceItem[];
  groups: AnnotationWorkspaceGroup[];
  total: number;
}
