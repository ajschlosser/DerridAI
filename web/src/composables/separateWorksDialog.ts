/* Copyright 2026 Aaron John Schlosser, PhD. */
import { readonly, shallowRef } from "vue";

export interface SeparateWorkGroup {
  /** The work title as the records carry it, or the "untitled" label for records with none. */
  work: string;
  count: number;
  /** Untitled groups start unchecked so they are never split off by accident. */
  defaultChecked: boolean;
}
export interface SeparateWorksSource {
  id: string;
  name: string;
  recordCount: number;
  groups: SeparateWorkGroup[];
}
export interface SeparateWorksSelection {
  fileId: string;
  works: string[];
  removeFromSource: boolean;
}
export interface SeparateWorksRequest {
  sources: SeparateWorksSource[];
  /** Performs the split. A rejection keeps the dialog open and is shown to the user. */
  confirm: (selection: SeparateWorksSelection) => Promise<void>;
}

const current = shallowRef<SeparateWorksRequest | null>(null);

/** Choose which works of a multi-work JSONL to copy into their own files. */
export function openSeparateWorksDialog(request: SeparateWorksRequest) {
  current.value = request;
}

export function closeSeparateWorksDialog() {
  current.value = null;
}

export function useSeparateWorksDialog() {
  return { current: readonly(current), close: closeSeparateWorksDialog };
}
