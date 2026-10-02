/* Copyright 2026 Aaron John Schlosser, PhD. */
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
