/* Copyright 2026 Aaron John Schlosser, PhD. */

export interface WorksMetadataValue {
  field: string;
  field_label: string;
  value: string;
  mixed: boolean;
  unique_count: number;
}

export interface WorksBiblioValue {
  field_label: string;
  value: string;
  mixed: boolean;
  unique_count: number;
}

export interface WorksInsightValue {
  key: string;
  value: number;
  other?: boolean;
}

export interface WorksInsight {
  id: string;
  field: string;
  title: string;
  heading: string;
  type: "bars" | "pie";
  values: WorksInsightValue[];
}

export type WorksDbStatusKind =
  | "changed"
  | "synced"
  | "exists"
  | "absent"
  | "unknown"
  | "none";

export interface WorksStatus {
  /** Empty for researcher/library records that do not expose corpus-index state. */
  kind: WorksDbStatusKind | "";
  label: string;
}

/**
 * Cheap, collection-scale representation used by the Works library.
 *
 * Keep selected-work-only metadata, citations and insight graphs out of this
 * shape so filtering/sorting a large library does not rebuild expensive detail.
 */
export interface WorksLibraryItem {
  work: string;
  count: number;
  review: number;
  annotations: number;
  files: string[];
  authors: string[];
  years: string[];
  cover: string;
  year_label: string;
  subtitle: string;
  publisher: WorksBiblioValue;
  translator: WorksBiblioValue;
  status: WorksStatus;
}

/** Full inspector payload for the currently selected work. */
export interface WorkDetail extends WorksLibraryItem {
  citation: string;
  metadata: WorksMetadataValue[];
  insights: WorksInsight[];
}

/** Backward-compatible alias for stories/tests that construct full work detail fixtures. */
export type WorksItem = WorkDetail;

export interface WorksStore {
  name: string;
  count: number;
}

/** Lightweight identity used when an operation needs the full corpus scope. */
export interface WorksScopeItem {
  work: string;
}

export type WorksSort = "title-asc" | "title-desc" | "records-desc" | "review-desc" | "year-asc";
export type WorksViewMode = "cards" | "compact";

export interface WorksFilters {
  needsReview: boolean;
  /** A stable work database status kind, or "" for any. */
  dbStatus: WorksDbStatusKind | "";
  author: string;
}

export type WorksIndexFreshnessState = "unavailable" | "empty" | "current" | "stale" | "unknown";

/**
 * Corpus-wide summary of how authoritative records relate to the selected
 * derived search index. "exists" is tracked separately from "synced" because
 * presence alone does not prove that the indexed representation is current.
 */
export interface WorksIndexFreshness {
  state: WorksIndexFreshnessState;
  totalRecords: number;
  currentRecords: number;
  changedRecords: number;
  presentRecords: number;
  absentRecords: number;
  unknownRecords: number;
  unavailableRecords: number;
}

export interface WorksSnapshot {
  mode: "admin" | "researcher";
  available: boolean;
  shared: boolean;
  error: string;
  works: WorksLibraryItem[];
  /** Full-corpus work identities, independent of the current library filters. */
  scopeWorks: WorksScopeItem[];
  selected: WorkDetail | null;
  query: string;
  selectedWork: string;
  stores: WorksStore[];
  activeStore: string;
  activeStoreCount: number;
  indexFreshness: WorksIndexFreshness;
  /** Every work in the corpus or database, regardless of search, filter or sort. */
  totalWorks: number;
  /** Works that match the current search and filters (the length of `works`). */
  visibleWorks: number;
  totalRecords: number;
  /** Distinct source files across all loaded works; 0 when the source is a database. */
  sourceFileCount: number;
  /** Records needing review across all works. */
  totalReview: number;
  /** Distinct authors across all works, for the author filter. */
  authors: string[];
  sort: WorksSort;
  filters: WorksFilters;
  viewMode: WorksViewMode;
  dbUnavailableReason: string;
  storesEmptyLabel: string;
  citationLabel: string;
  populateDisabledReason: string;
  syncAllDisabledReason: string;
  corpusManageDeniedReason: string;
  hasProviderProfiles: boolean;
  capabilities: {
    canManageCorpus: boolean;
    canSync: boolean;
    canSyncAll: boolean;
    canPopulate: boolean;
  };
}
