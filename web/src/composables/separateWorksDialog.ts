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

export interface SeparateWorkGroup {
  /** The work title as the records carry it, or the "untitled" label for records with none. */
  work: string;
  count: number;
  /** Untitled groups start unchecked so they are never split off by accident. */
  defaultChecked: boolean;
}
export interface SeparateWorksSource {
  id: string;
  name: string;
  recordCount: number;
  groups: SeparateWorkGroup[];
}
export interface SeparateWorksSelection {
  fileId: string;
  works: string[];
  removeFromSource: boolean;
}
export interface SeparateWorksRequest {
  sources: SeparateWorksSource[];
  /** Performs the split. A rejection keeps the dialog open and is shown to the user. */
  confirm: (selection: SeparateWorksSelection) => Promise<void>;
}

const current = shallowRef<SeparateWorksRequest | null>(null);

/** Choose which works of a multi-work JSONL to copy into their own files. */
export function openSeparateWorksDialog(request: SeparateWorksRequest) {
  current.value = request;
}

export function closeSeparateWorksDialog() {
  current.value = null;
}

export function useSeparateWorksDialog() {
  return { current: readonly(current), close: closeSeparateWorksDialog };
}
