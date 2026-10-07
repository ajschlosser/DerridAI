/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any

export const DOMAIN_PREFERENCE_KEYS = {
  search: "search-preferences",
  list: "list-preferences",
  layout: "layout-preferences",
  review: "review-preferences",
  vector: "vector-preferences",
  jobs: "job-bookkeeping",
} as const;

export type DomainPreferenceName = keyof typeof DOMAIN_PREFERENCE_KEYS;

const SEARCH_FIELDS = [
  "globalSearch",
  "globalFilters",
  "globalSort",
  "globalPage",
  "globalSearchMode",
  "globalSearchAutoRun",
  "searchResultLayouts",
  "dbSearchMethod",
  "dbSearchWhere",
  "dbSearchFetchK",
  "dbSearchLambda",
  "globalAdvancedOpen",
  "searchFacetFilters",
  "storeSearchSort",
] as const;

const LIST_FIELDS = [
  "selected",
  "searches",
  "listFilters",
  "pages",
  "pageSize",
  "sorts",
  "tableColumns",
] as const;

const LAYOUT_FIELDS = [
  "sidebarCollapsed",
  "collectionsCollapsed",
  "operationToastsMinimized",
  "operationStackPosition",
  "collapsedPanels",
] as const;

const VECTOR_FIELDS = [
  "activeStore",
  "storePage",
  "storePageSize",
  "storeQuery",
  "storeSearchMode",
  "storeWork",
  "storeSort",
  "storeFilters",
  "storeBrowseMode",
  "vectorTab",
  "vectorCollectionFilter",
] as const;

const JOB_FIELDS = ["upsertState", "upsertIgnored", "jobApplied", "upsertJobApplied"] as const;

function cloneable(value: Any): Any {
  if (value === null || ["string", "number", "boolean"].includes(typeof value)) return value;
  if (value instanceof Date) return value.toISOString();
  if (value instanceof Set) return [...value].map(cloneable);
  if (Array.isArray(value)) return value.map(cloneable).filter((item) => item !== undefined);
  if (typeof value === "object")
    return Object.fromEntries(
      Object.entries(value)
        .filter(([, item]) => typeof item !== "function" && item !== undefined)
        .map(([key, item]) => [key, cloneable(item)]),
    );
  return undefined;
}

function pick(state: Loose, fields: readonly string[]): Loose {
  return Object.fromEntries(fields.map((field) => [field, cloneable(state[field])]));
}

export function domainPreferenceRecord(state: Loose, name: DomainPreferenceName): Loose {
  const key = DOMAIN_PREFERENCE_KEYS[name];
  if (name === "search") return { key, ...pick(state, SEARCH_FIELDS) };
  if (name === "list") return { key, ...pick(state, LIST_FIELDS) };
  if (name === "layout") return { key, ...pick(state, LAYOUT_FIELDS) };
  if (name === "vector") return { key, ...pick(state, VECTOR_FIELDS) };
  if (name === "jobs") return { key, ...pick(state, JOB_FIELDS) };
  return {
    key,
    reviewSelection: cloneable(state.reviewSelection),
    selectedEvidence: cloneable(state.selectedEvidence),
  };
}

function assignFields(state: Loose, record: Loose, fields: readonly string[]) {
  for (const field of fields) if (record[field] !== undefined) state[field] = record[field];
}

/**
 * Applies one domain record after the legacy workspace preference record.
 *
 * Domain records therefore win when present, while an existing browser profile
 * with only the historical `workspace` record keeps restoring exactly as it did.
 */
export function applyDomainPreferenceRecord(state: Loose, value: unknown): void {
  if (!value || typeof value !== "object") return;
  const record = value as Loose;
  const key = String(record.key || "");
  if (key === DOMAIN_PREFERENCE_KEYS.search) assignFields(state, record, SEARCH_FIELDS);
  else if (key === DOMAIN_PREFERENCE_KEYS.list) assignFields(state, record, LIST_FIELDS);
  else if (key === DOMAIN_PREFERENCE_KEYS.layout) assignFields(state, record, LAYOUT_FIELDS);
  else if (key === DOMAIN_PREFERENCE_KEYS.vector) assignFields(state, record, VECTOR_FIELDS);
  else if (key === DOMAIN_PREFERENCE_KEYS.jobs) assignFields(state, record, JOB_FIELDS);
  else if (key === DOMAIN_PREFERENCE_KEYS.review) {
    if (record.reviewSelection !== undefined)
      state.reviewSelection = new Set(
        Array.isArray(record.reviewSelection) ? record.reviewSelection.map(String) : [],
      );
    if (record.selectedEvidence !== undefined)
      state.selectedEvidence =
        record.selectedEvidence && typeof record.selectedEvidence === "object"
          ? record.selectedEvidence
          : {};
  }
}

export function createDomainPreferencePersistence(deps: {
  state: Loose;
  put: (storeName: string, value: unknown) => Promise<void>;
  delay?: number;
}) {
  const { state, put } = deps;
  const delay = Math.max(0, Number(deps.delay ?? 350));
  const timers = new Map<DomainPreferenceName, ReturnType<typeof setTimeout>>();

  function persist(name: DomainPreferenceName) {
    if (!state.storageReady) return;
    const pending = timers.get(name);
    if (pending) clearTimeout(pending);
    timers.set(
      name,
      setTimeout(() => {
        timers.delete(name);
        void put("prefs", domainPreferenceRecord(state, name)).catch((error: Any) =>
          console.error(`IndexedDB ${name} preference persistence failed`, error),
        );
      }, delay),
    );
  }

  async function flush(name: DomainPreferenceName) {
    if (!state.storageReady) throw new Error("Workspace storage is not ready yet.");
    const pending = timers.get(name);
    if (pending) clearTimeout(pending);
    timers.delete(name);
    await put("prefs", domainPreferenceRecord(state, name));
  }

  function cancel() {
    for (const timer of timers.values()) clearTimeout(timer);
    timers.clear();
  }

  return {
    persistSearchPreferences: () => persist("search"),
    persistListPreferences: () => persist("list"),
    persistLayoutPreferences: () => persist("layout"),
    persistReviewPreferences: () => persist("review"),
    persistVectorPreferences: () => persist("vector"),
    persistJobPreferences: () => persist("jobs"),
    flushDomainPreferences: flush,
    cancelPendingDomainPreferences: cancel,
  };
}
