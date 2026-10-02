/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReadonly, shallowRef } from "vue";

export type LlmToolResultBody =
  | { kind: "clean_text"; text: string }
  | { kind: "draft_record"; json: string }
  | { kind: "link_record"; recordId: string; reason: string }
  | {
      kind: "rag_grade";
      question: string;
      cacheError: string;
      /** Escaped by the legacy grade renderer. */
      gradeHtml: string;
    }
  | {
      kind: "rag_grade_batch";
      graded: number;
      failed: number;
      total: number;
      /** Pretty-printed JSON, empty when every response was processed. */
      errorsJson: string;
      errorCount: number;
    }
  | { kind: "raw"; json: string };

export interface LlmToolResultRequest {
  title: string;
  /** "provider · model", already composed. */
  subtitle: string;
  body: LlmToolResultBody;
  /** The one follow-up the task offers, when it offers one. */
  action: { label: string; run: () => void | Promise<void> } | null;
}

const current = shallowRef<LlmToolResultRequest | null>(null);

/** The result of a finished LLM tool job; any follow-up runs after the dialog closes. */
export function openLlmToolResultDialog(request: LlmToolResultRequest) {
  current.value = request;
}

export function closeLlmToolResultDialog() {
  current.value = null;
}

export function useLlmToolResultDialog() {
  return { current: shallowReadonly(current), close: closeLlmToolResultDialog };
}
