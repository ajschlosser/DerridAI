/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

/*
 * Read-only application-chrome status derived from domain state.
 *
 * The projection is invalidation-driven: unrelated shell refreshes reuse the
 * same small object instead of repeatedly traversing files, stores, or evidence
 * selections. Owning domains invalidate it when those summaries can change.
 */
import { state } from "./sharedUrlState";
import { hasCorpusDb, recordStores } from "./storeAvailability";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export interface ShellStatusProjection {
  totalLoaded: number;
  corpusStoreCount: number;
  dbRecords: number;
  hasCorpusDb: boolean;
  activeStore: string;
  selectedEvidenceCount: number;
}

let cached: ShellStatusProjection | null = null;

export function invalidateShellStatusProjection(): void {
  cached = null;
}

export function getShellStatusProjection(): ShellStatusProjection {
  if (cached) return cached;

  const corpusStores = recordStores();
  cached = {
    totalLoaded: state.files.reduce(
      (sum: number, file: Any) => sum + (Array.isArray(file.records) ? file.records.length : 0),
      0,
    ),
    corpusStoreCount: corpusStores.length,
    dbRecords: corpusStores.reduce(
      (sum: number, store: Any) => sum + (Number(store.count) || 0),
      0,
    ),
    hasCorpusDb: hasCorpusDb(),
    activeStore: String(state.activeStore || ""),
    selectedEvidenceCount: Object.values(state.selectedEvidence || {}).filter(Boolean).length,
  };
  return cached;
}
