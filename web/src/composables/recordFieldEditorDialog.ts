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

/** How a field's value is edited, and therefore how its text is parsed back. */
export type RecordEditorFieldKind = "boolean" | "number" | "null" | "json" | "text" | "string";

export interface RecordEditorField {
  key: string;
  label: string;
  kind: RecordEditorFieldKind;
  /** The current value; the dialog never mutates it. */
  value: unknown;
  /** Spans the full width of the grid. */
  full: boolean;
}
export interface RecordEditorSection {
  title: string;
  fields: RecordEditorField[];
}
export interface RecordFieldEditorRequest {
  title: string;
  subtitle: string;
  /** An explanatory note above the sections, when the edit has consequences worth stating. */
  help: string;
  /** A note beside the buttons. */
  footerNote: string;
  saveLabel: string;
  /** The title of the message shown when a field cannot be parsed (for example invalid JSON). */
  parseErrorTitle: string;
  sections: RecordEditorSection[];
  /**
   * Receives every field's parsed value, keyed by field. Resolves `true` to close the dialog and
   * `false` to keep it open (a message was already shown); a rejection is shown to the user.
   */
  save: (values: Record<string, unknown>) => Promise<boolean>;
}

const current = shallowRef<RecordFieldEditorRequest | null>(null);

/** Edit the fields of one record: a local corpus record or a stored (vector collection) record. */
export function openRecordFieldEditorDialog(request: RecordFieldEditorRequest) {
  current.value = request;
}

export function closeRecordFieldEditorDialog() {
  current.value = null;
}

export function useRecordFieldEditorDialog() {
  return { current: shallowReadonly(current), close: closeRecordFieldEditorDialog };
}
