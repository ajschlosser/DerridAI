/* Copyright 2026 Aaron John Schlosser, PhD. */

export type RecordsFileOrigin = "imported" | "subset" | "merge" | "work_split" | "chroma";

export interface RecordsFileProvenance {
  id?: string;
  name?: string;
  records?: unknown[];
  count?: number;
  dirty?: Set<unknown> | unknown[] | number;
  active?: boolean;
  subset?: { source?: string; source_label?: string } | null;
  merged_from?: string[] | null;
  derived_from?: { type?: string; source_file?: string; work?: string } | null;
  imported_from_chroma?: string | null;
  content_hash?: string;
}

export interface RecordsFileTab {
  id: string;
  name: string;
  count: number;
  dirty: number;
  active: boolean;
  origin: RecordsFileOrigin;
  origin_detail: string;
}

function dirtyCount(dirty: RecordsFileProvenance["dirty"]): number {
  if (dirty instanceof Set) return dirty.size;
  if (Array.isArray(dirty)) return dirty.length;
  return Number(dirty || 0);
}

export function recordsFileOrigin(file: RecordsFileProvenance): RecordsFileOrigin {
  if (file.subset) return "subset";
  if (Array.isArray(file.merged_from) && file.merged_from.length) return "merge";
  if (file.derived_from?.type === "work_separation") return "work_split";
  if (file.imported_from_chroma) return "chroma";
  return "imported";
}

export function recordsFileOriginDetail(file: RecordsFileProvenance): string {
  const origin = recordsFileOrigin(file);
  if (origin === "merge") return (file.merged_from || []).filter(Boolean).join(", ");
  if (origin === "subset") return String(file.subset?.source_label || "").trim();
  if (origin === "work_split") {
    return String(file.derived_from?.work || file.derived_from?.source_file || "").trim();
  }
  if (origin === "chroma") return String(file.imported_from_chroma || "").trim();
  return "";
}

export function describeRecordsFile(
  file: RecordsFileProvenance,
  activeFileId: string | null = null,
): RecordsFileTab {
  return {
    id: String(file.id || ""),
    name: String(file.name || ""),
    count: Array.isArray(file.records) ? file.records.length : Number(file.count || 0),
    dirty: dirtyCount(file.dirty),
    active: Boolean(file.active) || Boolean(file.id && file.id === activeFileId),
    origin: recordsFileOrigin(file),
    origin_detail: recordsFileOriginDetail(file),
  };
}

export function serializableRecordsFile(
  file: RecordsFileProvenance & {
    records: unknown[];
    errors?: unknown[];
    imported_at?: string;
    content_hash?: string;
  },
) {
  return {
    id: file.id,
    name: file.name,
    records: file.records,
    errors: file.errors || [],
    dirty:
      file.dirty instanceof Set ? [...file.dirty] : Array.isArray(file.dirty) ? file.dirty : [],
    imported_at: file.imported_at || new Date().toISOString(),
    saved_at: new Date().toISOString(),
    content_hash: file.content_hash || "",
    merged_from: file.merged_from || null,
    subset: file.subset || null,
    derived_from: file.derived_from || null,
    imported_from_chroma: file.imported_from_chroma || null,
  };
}
