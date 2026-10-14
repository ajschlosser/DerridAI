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

export interface RecordAnnotationItem {
  id: string;
  scope?: "text" | "record" | "work";
  parent_id?: string | null;
  thread_id?: string;
  deleted_at?: string | null;
  reply_count?: number;
  linked_record_ids?: string[];
  field: string;
  quote: string;
  note: string;
  tags: string[];
  author: string;
  created_at?: string | null;
  removable: boolean;
  shared_annotation_id?: string | null;
}

export interface RecordHistoryItem {
  id: string;
  field_name: string;
  timestamp?: string | null;
  source: string;
  initiated_by?: string | null;
  model?: string | null;
  reason?: string | null;
}

export interface RecordPdfLink {
  pdf_file: string;
  pdf_page: number;
}

export interface RecordWorkspaceCapabilities {
  edit: boolean;
  annotate: boolean;
  evidence: boolean;
  review: boolean;
  upsert: boolean;
  llm_review: boolean;
  pdf: boolean;
  history: boolean;
  copy: boolean;
}

export interface RecordWorkspaceSnapshot {
  available: boolean;
  mode: "workspace" | "database";
  reason?: string;
  record?: Record<string, unknown>;
  record_id?: string;
  file_id?: string;
  file_name?: string | null;
  collection?: string;
  current_index?: number;
  total?: number;
  has_previous?: boolean;
  has_next?: boolean;
  find_query?: string;
  find_matches?: number;
  word_count?: number;
  character_count?: number;
  evidence_selected?: boolean;
  review_selected?: boolean;
  annotations?: RecordAnnotationItem[];
  pdf_links?: RecordPdfLink[];
  history?: RecordHistoryItem[];
  history_count?: number;
  inline_citation?: string;
  full_citation?: string;
  page_span?: string;
  capabilities?: RecordWorkspaceCapabilities;
  pdf?: {
    loaded: boolean;
    related: boolean;
    current_page?: number | null;
    current_linked?: boolean;
    title: string;
    name: string;
    loaded_pages?: number[];
  };
}
