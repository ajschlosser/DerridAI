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

import type { RecordsFileTab } from "../domain/recordsFiles";

export type { RecordsFileOrigin, RecordsFileTab } from "../domain/recordsFiles";

export interface RecordsColumn {
  key: string;
  label: string;
}

export interface RecordsStoreOption {
  name: string;
  count: number;
}

export interface RecordsDbStatus {
  kind: string;
  label: string;
  title: string;
}

export interface RecordsCell {
  key: string;
  kind: "status" | "pages" | "review" | "text" | "id" | "metadata" | "plain" | string;
  text: string;
  title?: string;
  status_kind?: string;
  meta_value?: string;
  meta_contains?: boolean;
}

export interface RecordsRow {
  index: number;
  key: string;
  record_id: string;
  work: string;
  selected: boolean;
  evidence_selected: boolean;
  db_status: RecordsDbStatus;
  cells: RecordsCell[];
}

export interface RecordsCapabilities {
  can_select: boolean;
  can_review: boolean;
  can_bulk_edit: boolean;
  can_upsert: boolean;
  can_import: boolean;
  can_select_evidence: boolean;
}

export interface RecordsListSnapshot {
  available: boolean;
  shared: boolean;
  files: RecordsFileTab[];
  file: RecordsFileTab | null;
  query: string;
  rows: RecordsRow[];
  columns: RecordsColumn[];
  available_columns: RecordsColumn[];
  sort: { key: string; dir: number };
  filters: Record<string, string>;
  page: number;
  pages: number;
  page_size: number;
  start: number;
  end: number;
  matched: number;
  total: number;
  flagged: number;
  selection_count: number;
  page_selected: boolean;
  stores: RecordsStoreOption[];
  active_store: string;
  has_database: boolean;
  db_unavailable_reason: string;
  capabilities: RecordsCapabilities;
}
