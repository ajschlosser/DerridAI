/* Copyright 2026 Aaron John Schlosser, PhD. */
import { readonly, shallowRef } from "vue";

export interface RemoveWorkFile {
  id: string;
  name: string;
  count: number;
}
export interface RemoveWorkSelection {
  fileIds: string[];
  removeDb: boolean;
}
export interface RemoveWorkRequest {
  work: string;
  files: RemoveWorkFile[];
  /** The vector store the work can also be removed from; empty when none is selected. */
  dbStore: string;
  /** Performs the removal. A rejection keeps the dialog open and is shown to the user. */
  confirm: (selection: RemoveWorkSelection) => Promise<void>;
}

const current = shallowRef<RemoveWorkRequest | null>(null);

/** Ask which copies of a work to remove; the destructive work itself stays with the caller. */
export function openRemoveWorkDialog(request: RemoveWorkRequest) {
  current.value = request;
}

export function closeRemoveWorkDialog() {
  current.value = null;
}

export function useRemoveWorkDialog() {
  return { current: readonly(current), close: closeRemoveWorkDialog };
}
