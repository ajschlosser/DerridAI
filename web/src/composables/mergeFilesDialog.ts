/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReadonly, shallowRef } from "vue";

export interface MergeFilesEntry {
  id: string;
  name: string;
  recordCount: number;
}
export interface MergeFilesSelection {
  fileIds: string[];
  /** The raw name typed by the user; the caller normalises it. */
  name: string;
  download: boolean;
}
export interface MergeFilesRequest {
  files: MergeFilesEntry[];
  defaultName: string;
  /**
   * Merges the chosen tabs. Resolves `true` to close the dialog and `false` to keep it open (a
   * message was already shown); a rejection is shown to the user.
   */
  merge: (selection: MergeFilesSelection) => Promise<boolean>;
}

const current = shallowRef<MergeFilesRequest | null>(null);

/** Choose which open JSONL tabs to merge into one. */
export function openMergeFilesDialog(request: MergeFilesRequest) {
  current.value = request;
}

export function closeMergeFilesDialog() {
  current.value = null;
}

export function useMergeFilesDialog() {
  return { current: shallowReadonly(current), close: closeMergeFilesDialog };
}
