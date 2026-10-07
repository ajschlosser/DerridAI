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

import { computeRecordFingerprint } from "./recordValues";
import { touchCorpus } from "../state/workspaceState";
import { state } from "./sharedUrlState";
import { invalidateShellStatusProjection } from "./shellStatusProjection";

// Corpus-derived data is read far more often than it changes. Keep one flattened index and memoized derived values
// instead of rebuilding thousands of row wrapper objects on every render/chart/filter pass. Any persisted corpus edit
// invalidates the cache synchronously. One instance, shared by the runtime and by Vue callers.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Row = { file: Loose; record: Loose; index: number };

export const corpusCache: {
  rows: Row[] | null;
  fields: string[] | null;
  memo: Map<string, unknown>;
  version: number;
} = { rows: null, fields: null, memo: new Map(), version: 0 };

// Fingerprints are cached by record object identity, but records are edited in place. Drop the cache whenever
// corpus-derived state changes so sync/status checks never reuse a pre-edit hash.
let recordFingerprintCache = new WeakMap<object, string>();

export function invalidateCorpusCache(
  fileId: string | null = null,
  structure = false,
): void {
  touchCorpus(fileId, structure);
  invalidateShellStatusProjection();
  corpusCache.rows = null;
  corpusCache.fields = null;
  corpusCache.memo.clear();
  corpusCache.version++;
  recordFingerprintCache = new WeakMap();
}

export function allRows(): Row[] {
  if (corpusCache.rows) return corpusCache.rows;
  const rows: Row[] = [];
  for (const file of state.files) {
    for (let index = 0; index < file.records.length; index++)
      rows.push({ file, record: file.records[index], index });
  }
  corpusCache.rows = rows;
  return rows;
}

export function memoCorpus<T>(key: string, builder: () => T): T {
  if (corpusCache.memo.has(key)) return corpusCache.memo.get(key) as T;
  const value = builder();
  corpusCache.memo.set(key, value);
  return value;
}

export function recordFingerprint(record: Loose): string {
  const cacheable = record && typeof record === "object";
  if (cacheable && recordFingerprintCache.has(record)) return recordFingerprintCache.get(record)!;
  const value = computeRecordFingerprint(record);
  if (cacheable) recordFingerprintCache.set(record, value);
  return value;
}
