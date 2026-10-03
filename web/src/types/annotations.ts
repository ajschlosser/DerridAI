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

export interface AnnotationWorkspaceItem {
  id: string;
  scope?: "text" | "record" | "work";
  record_id: string;
  work: string;
  linked_record_ids?: string[];
  parent_id?: string | null;
  thread_id?: string;
  deleted_at?: string | null;
  reply_count?: number;
  field: string;
  quote: string;
  note: string;
  tags: string[];
  author: string;
  source: string;
  created_at: string | null;
  server: boolean;
  removable: boolean;
  local_file_id: string | null;
  local_index: number | null;
  local_annotation_index: number | null;
  shared_annotation_id: string | null;
}

export interface AnnotationWorkspaceGroup {
  work: string;
  annotations: AnnotationWorkspaceItem[];
  records: number;
}

export interface AnnotationsWorkspaceSnapshot {
  query: string;
  view: "works" | "recent";
  annotations: AnnotationWorkspaceItem[];
  groups: AnnotationWorkspaceGroup[];
  total: number;
}
