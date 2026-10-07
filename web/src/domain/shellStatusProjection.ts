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
import { recordStores } from "./storeAvailability";

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

type AggregateStatus = Pick<
  ShellStatusProjection,
  "totalLoaded" | "corpusStoreCount" | "dbRecords" | "selectedEvidenceCount"
>;

let cachedAggregates: AggregateStatus | null = null;
let cachedFiles: unknown = null;
let cachedStores: unknown = null;
let cachedSelectedEvidence: unknown = null;

export function invalidateShellStatusProjection(): void {
  cachedAggregates = null;
  cachedFiles = null;
  cachedStores = null;
  cachedSelectedEvidence = null;
}

function aggregateStatus(): AggregateStatus {
  // Replacement of a top-level collection is itself a cheap invalidation signal.
  // In-place corpus edits use invalidateCorpusCache(), which explicitly clears this
  // projection because the array identity intentionally remains stable.
  if (
    cachedAggregates &&
    cachedFiles === state.files &&
    cachedStores === state.stores &&
    cachedSelectedEvidence === state.selectedEvidence
  )
    return cachedAggregates;

  const corpusStores = recordStores();
  cachedFiles = state.files;
  cachedStores = state.stores;
  cachedSelectedEvidence = state.selectedEvidence;
  cachedAggregates = {
    totalLoaded: state.files.reduce(
      (sum: number, file: Any) => sum + (Array.isArray(file.records) ? file.records.length : 0),
      0,
    ),
    corpusStoreCount: corpusStores.length,
    dbRecords: corpusStores.reduce(
      (sum: number, store: Any) => sum + (Number(store.count) || 0),
      0,
    ),
    selectedEvidenceCount: Object.values(state.selectedEvidence || {}).filter(Boolean).length,
  };
  return cachedAggregates;
}

export function getShellStatusProjection(): ShellStatusProjection {
  const aggregates = aggregateStatus();
  // Only true primitives are read live. Evidence selection can scale with the
  // workspace, so its count is invalidation-driven with the other aggregates.
  // Compatibility code still has a few direct active-store/health writes; keeping
  // those primitives live prevents stale chrome without a full projection scan.
  return {
    ...aggregates,
    hasCorpusDb: state.health?.chroma?.available === true && aggregates.corpusStoreCount > 0,
    activeStore: String(state.activeStore || ""),
  };
}
