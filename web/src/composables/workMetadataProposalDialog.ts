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
