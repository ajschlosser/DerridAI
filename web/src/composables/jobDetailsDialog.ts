/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReadonly, shallowRef } from "vue";

export interface JobDetailsEvent {
  /** Already formatted. */
  when: string;
  stage: string;
  /** "current/total · detail", already composed. */
  detail: string;
  latest: boolean;
}

export interface JobDetailsRequest {
  title: string;
  subtitle: string;
  facts: { name: string; value: string }[];
  fatalError: string;
  /** Pretty-printed request, API key already removed. */
  requestJson: string;
  events: JobDetailsEvent[];
  resultJson: string;
  /** "cancel" while the job can be cancelled, "cancelling" once it has been asked to stop. */
  cancel: "none" | "cancel" | "cancelling";
  /** Runs after the dialog closes; the forwarder reopens the details when the job was cancelled. */
  onCancel: () => void | Promise<void>;
  openResult: { label: string; run: () => void | Promise<void> } | null;
}

const current = shallowRef<JobDetailsRequest | null>(null);

/** Details of one background job: facts, request, timeline and result summary. */
export function openJobDetailsDialog(request: JobDetailsRequest) {
  current.value = request;
}

export function closeJobDetailsDialog() {
  current.value = null;
}

export function useJobDetailsDialog() {
  return { current: shallowReadonly(current), close: closeJobDetailsDialog };
}
