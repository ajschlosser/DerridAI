/* Copyright 2026 Aaron John Schlosser, PhD. */

export interface WorksMetadataValue {
  field: string;
  value: string;
  mixed: boolean;
}

export interface WorksInsightValue {
  key: string;
  value: number;
}

export interface WorksInsight {
  id: string;
  title: string;
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
  metadata: WorksMetadataValue[];
  status: WorksStatus;
  insights: WorksInsight[];
}

export interface WorksStore {
  name: string;
  count: number;
}

export interface WorksSnapshot {
  available: boolean;
  works: WorksItem[];
  query: string;
  selectedWork: string;
  stores: WorksStore[];
  activeStore: string;
  totalWorks: number;
  totalRecords: number;
  dbUnavailableReason: string;
  capabilities: {
    canManageCorpus: boolean;
    canSync: boolean;
  };
}
