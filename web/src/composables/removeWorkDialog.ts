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

import { readonly, shallowRef } from "vue";

export interface RemoveWorkFile {
  id: string;
  name: string;
  count: number;
}
export interface RemoveWorkSelection {
  fileIds: string[];
  removeDb: boolean;
}
export interface RemoveWorkRequest {
  work: string;
  files: RemoveWorkFile[];
  /** The vector store the work can also be removed from; empty when none is selected. */
  dbStore: string;
  /** Performs the removal. A rejection keeps the dialog open and is shown to the user. */
  confirm: (selection: RemoveWorkSelection) => Promise<void>;
}

const current = shallowRef<RemoveWorkRequest | null>(null);

/** Ask which copies of a work to remove; the destructive work itself stays with the caller. */
export function openRemoveWorkDialog(request: RemoveWorkRequest) {
  current.value = request;
}

export function closeRemoveWorkDialog() {
  current.value = null;
}

export function useRemoveWorkDialog() {
  return { current: readonly(current), close: closeRemoveWorkDialog };
}
