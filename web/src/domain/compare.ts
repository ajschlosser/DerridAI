/* Copyright 2026 Aaron John Schlosser, PhD. */
import { diffWordsWithSpace } from "diff";

export type CompareSource = "library" | "scratch";
export type CompareFilter = "changed" | "all";
export type DiffKind = "equal" | "del" | "ins";

export interface CompareLibraryOption {
  value: string;
  label: string;
  search?: string;
}

export interface CompareParseResult {
  record: Record<string, unknown> | null;
  errorKey: string;
  errorFallback: string;
}

export interface DiffPart {
  kind: DiffKind;
  value: string;
}

export interface CompareFieldRow {
  key: string;
  label?: string;
  changed: boolean;
  left: unknown;
  right: unknown;
  parts: DiffPart[];
}

const SKIP_KEYS = new Set(["updates", "_updates_count", "_researcher_text_policy", "_chroma_id"]);
const PRIORITY = [
  "record_id",
  "work",
  "document_author",
  "edition",
  "year",
  "page_start",
  "page_end",
  "speaker",
  "quoted_speaker",
  "position_holder",
  "stance",
  "target",
  "discourse_role",
  "proposition_status",
  "text",
];

export function parseCompareRecord(value: string): CompareParseResult {
  let text = String(value || "").trim();
  if (!text) return { record: null, errorKey: "", errorFallback: "" };
  text = text
    .replace(/^```(?:json|jsonl)?\s*/i, "")
    .replace(/\s*```$/, "")
    .trim();
  try {
    return coerceRecord(JSON.parse(text));
  } catch {
    const lines = text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
    const parsed: unknown[] = [];
    for (const line of lines) {
      try {
        parsed.push(JSON.parse(line));
      } catch {
        return {
          record: null,
          errorKey: "compare.error.invalid_json",
          errorFallback: "This side is not valid JSON or JSONL.",
        };
      }
    }
    if (parsed.length !== 1) {
      return {
        record: null,
        errorKey: "compare.error.one_record",
        errorFallback: "Paste exactly one JSON/JSONL record on each side.",
      };
    }
    return coerceRecord(parsed[0]);
  }
}

function coerceRecord(parsed: unknown): CompareParseResult {
  if (Array.isArray(parsed)) {
    if (
      parsed.length !== 1 ||
      !parsed[0] ||
      typeof parsed[0] !== "object" ||
      Array.isArray(parsed[0])
    ) {
      return {
        record: null,
        errorKey: "compare.error.one_record",
        errorFallback: "Paste exactly one JSON record, not an array of multiple records.",
      };
    }
    return { record: parsed[0] as Record<string, unknown>, errorKey: "", errorFallback: "" };
  }
  if (!parsed || typeof parsed !== "object") {
    return {
      record: null,
      errorKey: "compare.error.not_object",
      errorFallback: "Pasted value is not a JSON object.",
    };
  }
  return { record: parsed as Record<string, unknown>, errorKey: "", errorFallback: "" };
}

export function prettyRecord(record: Record<string, unknown> | null): string {
  if (!record) return "";
  return JSON.stringify(record, null, 2);
}

export function sameCompareValue(a: unknown, b: unknown): boolean {
  try {
    return JSON.stringify(a) === JSON.stringify(b);
  } catch {
    return Object.is(a, b);
  }
}

export function displayCompareValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function compareFieldKeys(a: Record<string, unknown>, b: Record<string, unknown>): string[] {
  return [...new Set([...Object.keys(a), ...Object.keys(b)])]
    .filter((key) => !SKIP_KEYS.has(key))
    .sort((x, y) => {
      const ax = PRIORITY.indexOf(x),
        ay = PRIORITY.indexOf(y);
      if (ax >= 0 || ay >= 0) return (ax < 0 ? 999 : ax) - (ay < 0 ? 999 : ay);
      return x.localeCompare(y);
    });
}

export function diffParts(left: unknown, right: unknown): DiffPart[] {
  const parts = diffWordsWithSpace(displayCompareValue(left), displayCompareValue(right));
  return parts.map((part) => ({
    kind: part.added ? "ins" : part.removed ? "del" : "equal",
    value: part.value,
  }));
}

export function buildCompareRows(
  a: Record<string, unknown> | null,
  b: Record<string, unknown> | null,
  filter: CompareFilter,
): CompareFieldRow[] {
  if (!a || !b) return [];
  const rows = compareFieldKeys(a, b).map((key) => {
    const left = a[key];
    const right = b[key];
    const changed = !sameCompareValue(left, right);
    return {
      key,
      changed,
      left,
      right,
      parts: changed
        ? diffParts(left, right)
        : [{ kind: "equal" as const, value: displayCompareValue(left) }],
    };
  });
  return filter === "changed" ? rows.filter((row) => row.changed) : rows;
}

export function filterLibraryOptions(
  options: CompareLibraryOption[],
  query: string,
  limit = 18,
): CompareLibraryOption[] {
  const terms = String(query || "")
    .trim()
    .toLocaleLowerCase()
    .split(/\s+/)
    .filter(Boolean);
  const matches: CompareLibraryOption[] = [];
  for (const option of options) {
    const haystack = `${option.label} ${option.search || ""}`.toLocaleLowerCase();
    if (terms.length && !terms.every((term) => haystack.includes(term))) continue;
    matches.push(option);
    if (matches.length >= limit) break;
  }
  return matches;
}

export function humanizeField(key: string): string {
  return key.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}
