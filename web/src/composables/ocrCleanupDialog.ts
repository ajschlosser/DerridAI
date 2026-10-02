/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReadonly, shallowRef } from "vue";

export type OcrCleanupScope = "active" | "selected" | "review" | "all";

export interface OcrCleanupRequest {
  /** The active tab, or null when no tab is open (its scope is then disabled). */
  active: { name: string; recordCount: number } | null;
  selectedCount: number;
  reviewCount: number;
  allCount: number;
  fileCount: number;
  /** Runs after the dialog has closed: resolves the scope to rows, confirms and cleans them. */
  choose: (scope: OcrCleanupScope) => Promise<void>;
}

const current = shallowRef<OcrCleanupRequest | null>(null);

/** Choose which records the OCR artifact cleanup runs over. */
export function openOcrCleanupDialog(request: OcrCleanupRequest) {
  current.value = request;
}

export function closeOcrCleanupDialog() {
  current.value = null;
}

export function useOcrCleanupDialog() {
  return { current: shallowReadonly(current), close: closeOcrCleanupDialog };
}
