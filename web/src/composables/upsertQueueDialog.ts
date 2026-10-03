/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReadonly, shallowRef } from "vue";

export interface UpsertQueueChange {
  field: string;
  /** Where the change came from (manual edit, bulk edit, …). */
  source: string;
  /** Already formatted for display; empty when unknown. */
  when: string;
  oldValue: string;
  newValue: string;
}
export interface UpsertQueueItem {
  /** Stable key of the local record; returned to `sync` and `remove`. */
  key: string;
  recordId: string;
  /** "Work · file", already composed. */
  source: string;
  status: { kind: string; label: string };
  changes: UpsertQueueChange[];
}
export interface UpsertQueueRequest {
  store: string;
  /** The queue as it is now; read again after every removal. */
  items: () => UpsertQueueItem[];
  remove: (key: string) => void;
  /** Upserts the chosen records. The dialog closes before it runs. */
  sync: (keys: string[]) => Promise<void>;
}

const current = shallowRef<UpsertQueueRequest | null>(null);

/** Review the local changes not yet written to the active vector collection, and sync a chosen set. */
export function openUpsertQueueDialog(request: UpsertQueueRequest) {
  current.value = request;
}

export function closeUpsertQueueDialog() {
  current.value = null;
}

export function useUpsertQueueDialog() {
  return { current: shallowReadonly(current), close: closeUpsertQueueDialog };
}
