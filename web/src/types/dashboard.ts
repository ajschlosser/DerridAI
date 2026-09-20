// Copyright 2026 Aaron John Schlosser, PhD.
export type DashboardSearchMode = "traditional" | "database";
export interface DashboardWork {
  work: string;
  count: number;
  year: string;
}
export interface DashboardTotals {
  records: number;
  works: number;
  changes: number;
  dbs: number;
}
export interface DashboardSnapshot {
  totals: DashboardTotals;
  works: DashboardWork[];
  query: string;
  mode: DashboardSearchMode;
  activeStore: string | null;
}
