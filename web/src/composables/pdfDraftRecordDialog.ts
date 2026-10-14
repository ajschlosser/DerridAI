/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
