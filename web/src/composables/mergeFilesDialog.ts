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

export interface MergeFilesEntry {
  id: string;
  name: string;
  recordCount: number;
}
export interface MergeFilesSelection {
  fileIds: string[];
  /** The raw name typed by the user; the caller normalises it. */
  name: string;
  download: boolean;
}
export interface MergeFilesRequest {
  files: MergeFilesEntry[];
  defaultName: string;
  /**
   * Merges the chosen tabs. Resolves `true` to close the dialog and `false` to keep it open (a
   * message was already shown); a rejection is shown to the user.
   */
  merge: (selection: MergeFilesSelection) => Promise<boolean>;
}

const current = shallowRef<MergeFilesRequest | null>(null);

/** Choose which open JSONL tabs to merge into one. */
export function openMergeFilesDialog(request: MergeFilesRequest) {
  current.value = request;
}

export function closeMergeFilesDialog() {
  current.value = null;
}

export function useMergeFilesDialog() {
  return { current: shallowReadonly(current), close: closeMergeFilesDialog };
}
