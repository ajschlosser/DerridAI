/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReadonly, shallowRef } from "vue";

export interface RecordPreviewField {
  key: string;
  label: string;
  /** Already formatted for display. */
  value: string;
  /** An LLM proposal exists for this field. */
  proposed: boolean;
}
export interface RecordPreviewProposal {
  label: string;
  current: string;
  proposed: string;
  rationale: string;
}
export interface RecordPreviewHistoryEntry {
  when: string;
  field: string;
  source: string;
}
export interface RecordPreviewRequest {
  recordId: string;
  /** "Work · file", already composed. */
  subtitle: string;
  /** The record changed after the proposals were made. */
  stale: boolean;
  summary: {
    work: string;
    pages: string;
    citation: string;
    proposalCount: number;
    needsReview: boolean;
  };
  fields: RecordPreviewField[];
  text: string;
  proposals: RecordPreviewProposal[];
  history: RecordPreviewHistoryEntry[];
  /** The review key the page-level "copy" handler reads from the button. */
  copyKey: string;
  openFull: () => void;
}

const current = shallowRef<RecordPreviewRequest | null>(null);

/** A read-only look at one local record beside the LLM proposals made for it. */
export function openRecordPreviewDialog(request: RecordPreviewRequest) {
  current.value = request;
}

export function closeRecordPreviewDialog() {
  current.value = null;
}

export function useRecordPreviewDialog() {
  return { current: shallowReadonly(current), close: closeRecordPreviewDialog };
}
