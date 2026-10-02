/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReadonly, shallowRef } from "vue";

export interface WorkMetadataProposalEntry {
  work: string;
  recordCount: number;
  fieldLabel: string;
  /** The value the records carry now, already formatted for display. */
  current: string;
  /** The model's proposal as editable text. */
  proposed: string;
  rationale: string;
  /** 0–1, when the catalogue match reported one. */
  confidence: number | null;
}
export interface WorkMetadataProposalUnmatched {
  work: string;
  message: string;
}
export interface WorkMetadataProposalSelection {
  /** Index into `entries`. */
  index: number;
  /** The text in the editable control, which may differ from `proposed`. */
  value: string;
}
export interface WorkMetadataProposalRequest {
  jobLabel: string;
  entries: WorkMetadataProposalEntry[];
  unmatched: WorkMetadataProposalUnmatched[];
  /**
   * Parses and applies the ticked proposals. Resolves `true` to close the dialog and `false` to keep it
   * open (a validation message was already shown); a rejection is shown to the user.
   */
  apply: (selections: WorkMetadataProposalSelection[]) => Promise<boolean>;
}

const current = shallowRef<WorkMetadataProposalRequest | null>(null);

/** Review the metadata a lookup proposed; nothing changes until the reviewer applies a selection. */
export function openWorkMetadataProposalDialog(request: WorkMetadataProposalRequest) {
  current.value = request;
}

export function closeWorkMetadataProposalDialog() {
  current.value = null;
}

export function useWorkMetadataProposalDialog() {
  return { current: shallowReadonly(current), close: closeWorkMetadataProposalDialog };
}
