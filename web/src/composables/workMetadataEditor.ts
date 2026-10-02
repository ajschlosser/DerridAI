/* Copyright 2026 Aaron John Schlosser, PhD. */
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
