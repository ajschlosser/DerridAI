// Copyright 2026 Aaron John Schlosser, PhD.

export interface Annotation {
  id: string;
  store?: string | null;
  record_id: string;
  work?: string | null;
  page_start?: number | string | null;
  page_end?: number | string | null;
  field: string;
  quote: string;
  note: string;
  tags: string[];
  author?: string | null;
  initiated_by?: string | null;
  created_at?: string | null;
  user_id?: number | null;
  shared_annotation_id?: string | null;
  removable?: boolean;
}

export type AnnotationDraft = Pick<
  Annotation,
  "record_id" | "work" | "page_start" | "page_end" | "field" | "quote" | "note" | "tags"
> & {
  store?: string | null;
};
