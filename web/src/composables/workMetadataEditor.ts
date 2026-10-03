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

import { readonly, shallowRef } from "vue";

export type WorkMetadataKind = "boolean" | "json" | "number" | "textarea" | "text";
export interface WorkMetadataField {
  field: string;
  label: string;
  kind: WorkMetadataKind;
  /** The records disagree, so the control starts blank and applying is opt-in. */
  mixed: boolean;
  mixedCount: number;
  initial: string;
}
export interface WorkMetadataApplication {
  /** Raw control values for the fields the user ticked, keyed by field. */
  values: Record<string, string>;
}
export interface WorkMetadataEditorRequest {
  work: string;
  recordCount: number;
  fileCount: number;
  fields: WorkMetadataField[];
  /** Opens the variants of a mixed field. */
  inspectMixed: (field: string) => void;
  /**
   * Parses, confirms and applies the changes. Resolves `true` to close the editor and `false` to keep
   * it open (a validation message or a declined confirmation); a rejection is shown to the user.
   */
  apply: (application: WorkMetadataApplication) => Promise<boolean>;
}

const current = shallowRef<WorkMetadataEditorRequest | null>(null);

/** Edit one set of metadata fields across every record of a work. */
export function openWorkMetadataEditorDialog(request: WorkMetadataEditorRequest) {
  current.value = request;
}

export function closeWorkMetadataEditorDialog() {
  current.value = null;
}

export function useWorkMetadataEditorDialog() {
  return { current: readonly(current), close: closeWorkMetadataEditorDialog };
}
