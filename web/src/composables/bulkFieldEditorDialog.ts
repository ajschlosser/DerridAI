/* Copyright 2026 Aaron John Schlosser, PhD. */
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
