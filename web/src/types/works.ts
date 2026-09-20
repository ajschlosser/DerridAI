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

export interface WorksStatus {
  kind: string;
  label: string;
}

export interface WorksItem {
  work: string;
  count: number;
  review: number;
  annotations: number;
  files: string[];
  authors: string[];
  years: string[];
  cover: string;
  citation: string;
  year_label: string;
  subtitle: string;
  publisher: WorksBiblioValue;
  translator: WorksBiblioValue;
  metadata: WorksMetadataValue[];
  status: WorksStatus;
  insights: WorksInsight[];
}

export interface WorksStore {
  name: string;
  count: number;
}

export interface WorksSnapshot {
  mode: "admin" | "researcher";
  available: boolean;
  shared: boolean;
  error: string;
  works: WorksItem[];
  selected: WorksItem | null;
  query: string;
  selectedWork: string;
  stores: WorksStore[];
  activeStore: string;
  activeStoreCount: number;
  totalWorks: number;
  totalRecords: number;
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
