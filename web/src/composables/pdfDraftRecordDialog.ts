/* Copyright 2026 Aaron John Schlosser, PhD. */
import { shallowReadonly, shallowRef } from "vue";

export interface PdfDraftTarget {
  /** JSONL file id or Chroma store name. */
  id: string;
  name: string;
  count: number;
}
export interface PdfDraftSubmission {
  json: string;
  fileId: string;
  storeName: string;
}
export interface PdfDraftRecordRequest {
  title: string;
  page: number;
  recordJson: string;
  files: PdfDraftTarget[];
  stores: PdfDraftTarget[];
  /** Validates and saves; resolves true when the draft was added and the dialog may close. */
  save: (submission: PdfDraftSubmission) => Promise<boolean>;
}

const current = shallowRef<PdfDraftRecordRequest | null>(null);

/** Review an LLM-drafted record from a PDF page before adding it to a JSONL file and/or Chroma store. */
export function openPdfDraftRecordDialog(request: PdfDraftRecordRequest) {
  current.value = request;
}

export function closePdfDraftRecordDialog() {
  current.value = null;
}

export function usePdfDraftRecordDialog() {
  return { current: shallowReadonly(current), close: closePdfDraftRecordDialog };
}
