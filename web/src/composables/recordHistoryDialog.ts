/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReadonly, shallowRef } from "vue";

/** One reconstructed state of a record: the original, then the state after each change set. */
export interface RecordHistoryVersion {
  label: string;
  timestamp?: string | null;
  source?: string | null;
  model?: string | null;
  record: Record<string, unknown>;
}

export interface RecordHistoryRequest {
  recordId: string;
  /** Read live on every action, so the list follows restores made while the dialog is open. */
  versions: () => RecordHistoryVersion[];
  /** Fields whose value differs between two versions. */
  changedFields: (previous: Record<string, unknown>, current: Record<string, unknown>) => string[];
  fieldLabel: (field: string) => string;
  formatValue: (value: unknown) => string;
  formatTimestamp: (value: string) => string;
  /** Restores the record to a version; resolves to whether anything changed. Toasts and refreshes stay with the caller. */
  restore: (version: RecordHistoryVersion) => Promise<boolean>;
  /** Confirms, then restores the first version; resolves to whether anything changed. */
  restoreOriginal: () => Promise<boolean>;
  /** Confirms and deletes the audit trail; resolves to whether it was deleted (the dialog then closes). */
  clear: () => Promise<boolean>;
}

const current = shallowRef<RecordHistoryRequest | null>(null);

/** Browse a record's versions and restore one. */
export function openRecordHistoryDialog(request: RecordHistoryRequest) {
  current.value = request;
}

export function closeRecordHistoryDialog() {
  current.value = null;
}

export function useRecordHistoryDialog() {
  return { current: shallowReadonly(current), close: closeRecordHistoryDialog };
}
