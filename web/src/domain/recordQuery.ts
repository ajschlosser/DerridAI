/* Copyright 2026 Aaron John Schlosser, PhD. */

// Pure record parsing, matching and text helpers extracted verbatim from the legacy runtime.

type JsonObject = Record<string, unknown>;

const errorMessage = (error: unknown): string => (error instanceof Error ? error.message : String(error));

export function parseJsonl(text: string): { records: JsonObject[]; errors: string[] } {
  const records: JsonObject[] = [];
  const errors: string[] = [];
  const trimmed = text.trim();
  if (!trimmed) return { records, errors };
  if (trimmed.startsWith("[")) {
    try {
      const value = JSON.parse(trimmed);
      if (!Array.isArray(value)) throw Error("Root is not an array");
      value.forEach((x, i) =>
        typeof x === "object" && x && !Array.isArray(x) ? records.push(x) : errors.push(`Item ${i + 1}: not an object`),
      );
      return { records, errors };
    } catch (e) {
      return { records, errors: [errorMessage(e)] };
    }
  }
  text.split(/\r?\n/).forEach((line, i) => {
    if (!line.trim()) return;
    try {
      const x = JSON.parse(line);
      typeof x === "object" && x && !Array.isArray(x) ? records.push(x) : errors.push(`Line ${i + 1}: not an object`);
    } catch (e) {
      errors.push(`Line ${i + 1}: ${errorMessage(e)}`);
    }
  });
  return { records, errors };
}

export function flattenValueList(value: unknown): string[] {
  if (value == null) return [];
  if (Array.isArray(value)) return value.flatMap(flattenValueList);
  if (typeof value === "object") return Object.values(value as object).flatMap(flattenValueList);
  const text = String(value).trim();
  if (!text) return [];
  if ((text.startsWith("[") && text.endsWith("]")) || (text.startsWith("{") && text.endsWith("}"))) {
    try {
      return flattenValueList(JSON.parse(text));
    } catch {
      // Not valid JSON; fall through to the delimiter handling below.
    }
  }
  // Legacy corpus files have used newline, semicolon, pipe, and CSV-like
  // encodings for list metadata. Normalize them once so every badge surface
  // receives a stable list rather than rendering serialized arrays as a chip.
  if (/[\n;|]/.test(text))
    return text
      .split(/[\n;|]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  // Commas are intentionally not treated as a universal list separator: person
  // names and bibliographic values commonly contain commas. Legacy list fields
  // should use JSON arrays, semicolons, pipes, or line breaks.
  return [text];
}

export function countOccurrences(text: unknown, query: unknown): number {
  if (!query) return 0;
  const hay = String(text).toLocaleLowerCase();
  const needle = String(query).toLocaleLowerCase();
  let i = 0;
  let count = 0;
  while ((i = hay.indexOf(needle, i)) >= 0) {
    count++;
    i += Math.max(needle.length, 1);
  }
  return count;
}

/** Filter-row matching for the operators `empty`, `notempty`, `eq`, `neq`, `has`, `nhas`, `gte` and `lte`. */
export function valueMatches(v: unknown, op: string, n: unknown): boolean {
  const empty = v == null || v === "" || (Array.isArray(v) && !v.length);
  if (op === "empty") return empty;
  if (op === "notempty") return !empty;
  const vals: unknown[] = Array.isArray(v) ? v : [v];
  const q = String(n ?? "").toLocaleLowerCase();
  const lower = (x: unknown) => String(x ?? "").toLocaleLowerCase();
  if (op === "eq") return vals.some((x) => lower(x) === q);
  if (op === "neq") return !vals.some((x) => lower(x) === q);
  if (op === "has") return vals.some((x) => lower(x).includes(q));
  if (op === "nhas") return !vals.some((x) => lower(x).includes(q));
  if (op === "gte") return vals.some((x) => Number(x) >= Number(n));
  if (op === "lte") return vals.some((x) => Number(x) <= Number(n));
  return true;
}

export function subsetValueText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(subsetValueText).join(" ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export interface SubsetRule {
  field: string;
  operator: string;
  value?: unknown;
}

export function subsetRuleMatches(record: JsonObject | null | undefined, rule: SubsetRule, caseSensitive = false): boolean {
  const value = record?.[rule.field];
  const raw = String(rule.value ?? "");
  const normalize = (text: unknown) => (caseSensitive ? String(text) : String(text).toLocaleLowerCase());
  const hay = normalize(subsetValueText(value));
  const needle = normalize(raw);
  switch (rule.operator) {
    case "equals":
      return Array.isArray(value) ? value.some((item) => normalize(subsetValueText(item)) === needle) : hay === needle;
    case "not_equals":
      return Array.isArray(value) ? !value.some((item) => normalize(subsetValueText(item)) === needle) : hay !== needle;
    case "contains":
      return hay.includes(needle);
    case "not_contains":
      return !hay.includes(needle);
    case "array_contains":
      return Array.isArray(value) && value.some((item) => normalize(subsetValueText(item)) === needle);
    case "exists":
      return value !== undefined && value !== null && subsetValueText(value) !== "";
    case "missing":
      return value === undefined || value === null || subsetValueText(value) === "";
    case "truthy":
      return Boolean(value);
    case "falsy":
      return !value;
    case "regex":
      try {
        return new RegExp(raw, caseSensitive ? "" : "i").test(subsetValueText(value));
      } catch {
        return false;
      }
    default:
      return false;
  }
}
