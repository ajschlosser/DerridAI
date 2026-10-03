/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReadonly, shallowRef } from "vue";

export interface JobReviewRow {
  recordId: string;
  /** Review key read by the page-level "copy" handler; empty when the record is gone. */
  copyKey: string;
  stale: boolean;
  /** The field is the record text, which is not selected by default. */
  isText: boolean;
  field: string;
  /** Escaped, diff-marked HTML from the shared `reviewDiffSides` renderer. */
  currentHtml: string;
  proposedHtml: string;
  rationale: string;
}

export interface JobReviewUnchanged {
  recordId: string;
  work: string;
  stale: boolean;
}

export interface JobReviewView {
  title: string;
  subtitle: string;
  /** The job is still running, so the dialog follows it. */
  active: boolean;
  completed: number;
  remaining: number;
  noChangeCount: number;
  resolution: {
    acceptedResults: number;
    acceptedFields: number;
    rejectedResults: number;
    rejectedFields: number;
    state: string;
  };
  failures: string[];
  rows: JobReviewRow[];
  unchanged: JobReviewUnchanged[];
  /** Which discard button, if any, the footer offers. */
  discard: "none" | "stop" | "remove";
  /** At least one successful result can be accepted or marked reviewed. */
  hasSuccessful: boolean;
}

export type JobReviewApplyMode = "review" | "selected" | "all";

export interface JobReviewActions {
  /** Each resolves true when the change was made and the view republished. */
  apply: (mode: JobReviewApplyMode, selected: number[]) => Promise<boolean>;
  rejectSelected: (selected: number[]) => Promise<boolean>;
  discard: () => void | Promise<void>;
  refresh: () => void | Promise<void>;
  previewRow: (index: number) => void;
  previewUnchanged: (index: number) => void;
  /** Called once when the dialog closes, however it closes. */
  onClose: () => void;
}

export interface JobReviewHandle {
  /** Replace the displayed data, keeping the reviewer's selection where it still applies. */
  update: (view: JobReviewView) => void;
  close: () => void;
  isOpen: () => boolean;
}

interface Session {
  view: JobReviewView;
  actions: JobReviewActions;
}

const current = shallowRef<Session | null>(null);

/** Review of the proposals a finished or running LLM job produced. */
export function openJobReviewDialog(
  view: JobReviewView,
  actions: JobReviewActions,
): JobReviewHandle {
  current.value = { view, actions };
  const isOpen = () => current.value?.actions === actions;
  return {
    update(next) {
      if (isOpen()) current.value = { view: next, actions };
    },
    close() {
      if (isOpen()) closeJobReviewDialog();
    },
    isOpen,
  };
}

export function closeJobReviewDialog() {
  const session = current.value;
  if (!session) return;
  current.value = null;
  session.actions.onClose();
}

export function useJobReviewDialog() {
  return { current: shallowReadonly(current), close: closeJobReviewDialog };
}
