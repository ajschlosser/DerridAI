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

import { shallowReadonly, shallowRef } from "vue";

export type BulkFieldScope = "selected" | "active" | "work" | "all" | "fixed";

export interface BulkFieldOption {
  id: string;
  label: string;
}
export interface BulkFieldInspection {
  /** How many records the edit would touch. */
  targets: number;
  /** How many distinct values the field holds across a sample of them. */
  distinct: number;
  /** The text to prefill when every sampled record holds the same value, else null. */
  only: string | null;
}
export interface BulkFieldEditorRequest {
  title: string;
  /** Set when the caller fixed the rows (for example search results); the scope picker is hidden. */
  fixedCount: number | null;
  defaultScope: BulkFieldScope;
  selectedCount: number;
  activeCount: number;
  /** The selected record's work, which offers the "this work" scope; empty offers none. */
  currentWork: string;
  allCount: number;
  fields: BulkFieldOption[];
  inspect: (scope: BulkFieldScope, field: string) => BulkFieldInspection;
  /**
   * Parses, confirms and applies the edit. Resolves `true` to close the dialog and `false` to keep
   * it open (a message was already shown); a rejection is shown to the user.
   */
  apply: (edit: { scope: BulkFieldScope; field: string; text: string }) => Promise<boolean>;
}

const current = shallowRef<BulkFieldEditorRequest | null>(null);

/** Set one field to one value across a chosen set of records. */
export function openBulkFieldEditorDialog(request: BulkFieldEditorRequest) {
  current.value = request;
}

export function closeBulkFieldEditorDialog() {
  current.value = null;
}

export function useBulkFieldEditorDialog() {
  return { current: shallowReadonly(current), close: closeBulkFieldEditorDialog };
}
