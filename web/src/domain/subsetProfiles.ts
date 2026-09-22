/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { SubsetRule } from "./recordQuery";
import { SUBSET_OPERATORS, type SubsetExpressionItem, type SubsetJoin } from "./subsetExpression";

/** Saved "Create JSONL subset" filter profiles: the file format used to move them between browsers. */
export const SUBSET_PROFILES_FORMAT = "derridai-subset-filter-profiles";
export const SUBSET_PROFILES_VERSION = 1;
/** Browser storage keeps at most this many profiles. */
export const SUBSET_PROFILES_LIMIT = 50;
const STORAGE_KEY = "derridai.subset-filter-profiles.v1";

export interface SubsetProfile {
  id: string;
  name: string;
  expression: SubsetExpressionItem[];
  caseSensitive: boolean;
  created_at?: string;
}

/** Saved profiles in this browser. Unreadable storage reads as none rather than failing the dialog. */
export function loadSubsetProfiles(): SubsetProfile[] {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function saveSubsetProfiles(profiles: SubsetProfile[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(profiles.slice(0, SUBSET_PROFILES_LIMIT)));
}

/** Why an import was refused; the dialog maps each code to a localized message. */
export class SubsetProfilesImportError extends Error {
  constructor(
    public code: "not_json" | "wrong_format" | "newer_version" | "no_profiles",
    message: string,
  ) {
    super(message);
  }
}

export function exportSubsetProfiles(profiles: SubsetProfile[], now = new Date()) {
  return {
    format: SUBSET_PROFILES_FORMAT,
    version: SUBSET_PROFILES_VERSION,
    exported_at: now.toISOString(),
    profiles,
  };
}

const isObject = (value: unknown): value is Record<string, unknown> =>
  Boolean(value) && typeof value === "object" && !Array.isArray(value);
const join = (value: unknown): SubsetJoin | null =>
  value === "AND" || value === "OR" ? value : null;

function readRule(value: unknown): SubsetRule | null {
  if (!isObject(value) || typeof value.field !== "string" || !value.field.trim()) return null;
  if (!(SUBSET_OPERATORS as readonly string[]).includes(String(value.operator))) return null;
  return {
    field: value.field,
    operator: String(value.operator),
    value: value.value == null ? "" : String(value.value),
  };
}

function readItem(value: unknown, index: number): SubsetExpressionItem | null {
  if (!isObject(value)) return null;
  const itemJoin = index === 0 ? "AND" : join(value.join);
  if (!itemJoin) return null;
  if (value.type === "group") {
    const mode = join(value.mode);
    const rules = Array.isArray(value.rules) ? value.rules.map(readRule) : [];
    if (!mode || !rules.length || rules.some((rule) => !rule)) return null;
    return { type: "group", join: itemJoin, mode, rules: rules as SubsetRule[] };
  }
  const rule = readRule(value.rule);
  return rule ? { type: "rule", join: itemJoin, rule } : null;
}

/**
 * Parse an exported profiles file. Every profile is validated against the closed operator
 * vocabulary; a profile with any unreadable condition is skipped whole rather than imported with
 * the condition silently dropped, since that would change which records it selects.
 */
export function parseSubsetProfilesImport(text: string): {
  profiles: SubsetProfile[];
  skipped: number;
} {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new SubsetProfilesImportError("not_json", "The file is not valid JSON.");
  }
  if (!isObject(data) || data.format !== SUBSET_PROFILES_FORMAT || !Array.isArray(data.profiles))
    throw new SubsetProfilesImportError("wrong_format", "The file is not a filter profile export.");
  if (Number(data.version) > SUBSET_PROFILES_VERSION)
    throw new SubsetProfilesImportError(
      "newer_version",
      "The file was exported by a newer version.",
    );
  const profiles: SubsetProfile[] = [];
  let skipped = 0;
  for (const raw of data.profiles) {
    const name = isObject(raw) && typeof raw.name === "string" ? raw.name.trim() : "";
    const items =
      isObject(raw) && Array.isArray(raw.expression) ? raw.expression.map(readItem) : [];
    if (!name || !items.length || items.some((item) => !item)) {
      skipped++;
      continue;
    }
    profiles.push({
      id: isObject(raw) && typeof raw.id === "string" ? raw.id : "",
      name,
      expression: items as SubsetExpressionItem[],
      caseSensitive: Boolean(isObject(raw) && raw.caseSensitive),
      ...(isObject(raw) && typeof raw.created_at === "string"
        ? { created_at: raw.created_at }
        : {}),
    });
  }
  if (!profiles.length)
    throw new SubsetProfilesImportError("no_profiles", "The file has no usable filter profiles.");
  return { profiles, skipped };
}

/**
 * Merge imported profiles into the saved ones. A profile with the same id, or failing that the same
 * name, replaces the saved one (re-importing an edited export updates it); the rest are added.
 * Anything past the storage limit is reported, not silently lost.
 */
export function mergeSubsetProfiles(
  existing: SubsetProfile[],
  incoming: SubsetProfile[],
  makeId: () => string,
): { profiles: SubsetProfile[]; added: number; replaced: number; dropped: number } {
  const merged = [...existing];
  let added = 0;
  let replaced = 0;
  for (const profile of incoming) {
    const byId = profile.id ? merged.findIndex((item) => item.id === profile.id) : -1;
    const at =
      byId >= 0
        ? byId
        : merged.findIndex(
            (item) => item.name.toLocaleLowerCase() === profile.name.toLocaleLowerCase(),
          );
    if (at >= 0) {
      merged[at] = { ...profile, id: merged[at].id };
      replaced++;
    } else {
      merged.push({ ...profile, id: profile.id || makeId() });
      added++;
    }
  }
  const dropped = Math.max(0, merged.length - SUBSET_PROFILES_LIMIT);
  return {
    profiles: merged.slice(0, SUBSET_PROFILES_LIMIT),
    added: added - dropped,
    replaced,
    dropped,
  };
}
