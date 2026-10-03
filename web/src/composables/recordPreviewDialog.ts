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
