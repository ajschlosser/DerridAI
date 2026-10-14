/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

// Pure value helpers for corpus records: audit cloning, equality, stable fingerprints and sorting.
// Extracted verbatim from the legacy runtime.

export function cloneAuditValue(value: unknown): unknown {
  if (value === undefined) return null;
  try {
    return structuredClone(value);
  } catch {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch {
      return String(value);
    }
  }
}

export function sameValue(a: unknown, b: unknown): boolean {
  try {
    return JSON.stringify(a) === JSON.stringify(b);
  } catch {
    return Object.is(a, b);
  }
}

/** Recursively sorts object keys and drops update history and Chroma bookkeeping, so equal records serialize equally. */
export function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    const source = value as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(source)
      .filter((key) => key !== "updates" && key !== "_updates_count" && !key.startsWith("_chroma_"))
      .sort())
      out[key] = stableValue(source[key]);
    return out;
  }
  return value;
}

/** FNV-1a hash of a record's stable JSON, as eight hex digits. Callers own any caching. */
export function computeRecordFingerprint(record: unknown): string {
  const text = JSON.stringify(stableValue(record));
  let hash = 2166136261;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function compareValues(a: unknown, b: unknown): number {
  const ae = a == null || a === "";
  const be = b == null || b === "";
  if (ae && be) return 0;
  if (ae) return 1;
  if (be) return -1;
  if (Array.isArray(a)) a = a.join("\u0000");
  if (Array.isArray(b)) b = b.join("\u0000");
  if (typeof a === "boolean" || typeof b === "boolean") return Number(a) - Number(b);
  const na = Number(a);
  const nb = Number(b);
  if (
    Number.isFinite(na) &&
    Number.isFinite(nb) &&
    String(a).trim() !== "" &&
    String(b).trim() !== ""
  )
    return na - nb;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

interface SortableRow {
  file: { name: string };
  record?: Record<string, unknown> | null;
  index: number;
}

export function sortRows<T extends SortableRow>(
  rows: T[],
  sort: { key?: string; dir: number } | null | undefined,
): T[] {
  if (!sort?.key) return rows;
  const key = sort.key;
  return [...rows].sort((x, y) => {
    const av = key === "__file" ? x.file.name : x.record?.[key];
    const bv = key === "__file" ? y.file.name : y.record?.[key];
    const c = compareValues(av, bv);
    return (c || x.index - y.index) * sort.dir;
  });
}
