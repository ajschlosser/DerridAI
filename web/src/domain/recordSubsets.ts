/* Copyright 2026 Aaron John Schlosser, PhD. */
import {
  SUBSET_EXPRESSION_LOGIC,
  recordMatchesExpression,
  type SubsetExpressionItem,
} from "./subsetExpression";

/**
 * Subset files: a new browser-local JSONL file holding copies of the Records in a source that
 * match a filter expression. Each copy keeps its `record_id` and audit trail, so a subset never
 * creates new Record identity; the file records the expression and source it was made from.
 *
 * This is the narrow boundary the Records view uses; the loaded files still live in the legacy
 * runtime state, which is passed in.
 */
type JsonRecord = Record<string, unknown>;
interface WorkspaceFile {
  id: string;
  name: string;
  records: JsonRecord[];
  [key: string]: unknown;
}
interface Deps {
  state: { files: WorkspaceFile[]; activeFileId: string | null };
  cloneAuditValue: <T>(value: T) => T;
  downloadBlob: (blob: Blob, name: string) => void;
  /** The localized label of a Record field. */
  label: (field: string) => string;
  navigateTo: (view: string, options: { fileId: string }) => void;
  persistFileNow: (file: WorkspaceFile) => Promise<unknown>;
  uid: () => string;
}

/** "active" and "all" are the two sources that follow the workspace; any other value is a file id. */
export type SubsetSourceId = "active" | "all" | string;
export interface SubsetSource {
  id: SubsetSourceId;
  /** The file name for a single file; empty for "all". */
  name: string;
  count: number;
}
export interface SubsetField {
  key: string;
  label: string;
}
export interface SubsetRequest {
  name: string;
  source: SubsetSourceId;
  expression: SubsetExpressionItem[];
  caseSensitive: boolean;
  download: boolean;
}

/** The file name a subset is saved under: the given name, or a default, ending in `.jsonl`. */
export function subsetFileName(name: string): string {
  const trimmed = name.trim() || "subset.jsonl";
  return /\.jsonl$/i.test(trimmed) ? trimmed : `${trimmed}.jsonl`;
}

export function createRecordSubsets(deps: Deps) {
  const { state } = deps;

  function activeFile() {
    return state.files.find((file) => file.id === state.activeFileId) || state.files[0] || null;
  }

  function subsetSources(): SubsetSource[] {
    const active = activeFile();
    return [
      { id: "active", name: active?.name || "", count: active?.records.length || 0 },
      {
        id: "all",
        name: "",
        count: state.files.reduce((sum, file) => sum + file.records.length, 0),
      },
      ...state.files.map((file) => ({ id: file.id, name: file.name, count: file.records.length })),
    ];
  }

  function sourceFileFor(source: SubsetSourceId): WorkspaceFile | null {
    return source === "active"
      ? activeFile()
      : state.files.find((item) => item.id === source) || null;
  }

  function subsetSourceRecords(source: SubsetSourceId): JsonRecord[] {
    if (source === "all") return state.files.flatMap((file) => file.records);
    return sourceFileFor(source)?.records || [];
  }

  /** Every field present on the loaded Records, except internal `_` fields, sorted by key. */
  function subsetFields(): SubsetField[] {
    const fields = new Set<string>();
    for (const file of state.files)
      for (const record of file.records)
        for (const key of Object.keys(record)) if (!key.startsWith("_")) fields.add(key);
    return [...fields].sort().map((key) => ({ key, label: deps.label(key) }));
  }

  /** The default name for a new subset of the active file, e.g. `glas-subset.jsonl`. */
  function defaultSubsetName(): string {
    return `${(activeFile()?.name || "subset.jsonl").replace(/\.jsonl$/i, "")}-subset.jsonl`;
  }

  /**
   * Create the subset file, make it the active file and open it in Records. Matching is recomputed
   * here from the request, so the file holds exactly what the expression selects.
   */
  async function createSubsetFile(
    request: SubsetRequest,
  ): Promise<{ name: string; count: number }> {
    const matched = subsetSourceRecords(request.source).filter((record) =>
      recordMatchesExpression(record, request.expression, request.caseSensitive),
    );
    if (!request.expression.length || !matched.length) return { name: "", count: 0 };
    const name = subsetFileName(request.name);
    const now = new Date().toISOString();
    // Record which file(s) the subset came from, resolved now: "active" would mean whichever file is
    // active later.
    const sourceFile = request.source === "all" ? null : sourceFileFor(request.source);
    const source = sourceFile ? sourceFile.id : "all";
    const sourceLabel = sourceFile
      ? sourceFile.name
      : state.files.map((item) => item.name).join(", ");
    const file: WorkspaceFile = {
      id: deps.uid(),
      name,
      records: matched.map((record) => deps.cloneAuditValue(record)),
      errors: [],
      dirty: new Set(),
      imported_at: now,
      subset: {
        created_at: now,
        source,
        source_label: sourceLabel,
        logic: SUBSET_EXPRESSION_LOGIC,
        expression: request.expression,
        case_sensitive: request.caseSensitive,
      },
    };
    state.files.push(file);
    state.activeFileId = file.id;
    await deps.persistFileNow(file);
    if (request.download) {
      const lines = file.records.map((record) => JSON.stringify(record)).join("\n");
      deps.downloadBlob(new Blob([`${lines}\n`], { type: "application/x-ndjson" }), name);
    }
    deps.navigateTo("list", { fileId: file.id });
    return { name, count: file.records.length };
  }

  return { subsetSources, subsetSourceRecords, subsetFields, defaultSubsetName, createSubsetFile };
}
