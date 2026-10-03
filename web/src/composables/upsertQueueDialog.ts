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

export interface UpsertQueueChange {
  field: string;
  /** Where the change came from (manual edit, bulk edit, …). */
  source: string;
  /** Already formatted for display; empty when unknown. */
  when: string;
  oldValue: string;
  newValue: string;
}
export interface UpsertQueueItem {
  /** Stable key of the local record; returned to `sync` and `remove`. */
  key: string;
  recordId: string;
  /** "Work · file", already composed. */
  source: string;
  status: { kind: string; label: string };
  changes: UpsertQueueChange[];
}
export interface UpsertQueueRequest {
  store: string;
  /** The queue as it is now; read again after every removal. */
  items: () => UpsertQueueItem[];
  remove: (key: string) => void;
  /** Upserts the chosen records. The dialog closes before it runs. */
  sync: (keys: string[]) => Promise<void>;
}

const current = shallowRef<UpsertQueueRequest | null>(null);

/** Review the local changes not yet written to the active vector collection, and sync a chosen set. */
export function openUpsertQueueDialog(request: UpsertQueueRequest) {
  current.value = request;
}

export function closeUpsertQueueDialog() {
  current.value = null;
}

export function useUpsertQueueDialog() {
  return { current: shallowReadonly(current), close: closeUpsertQueueDialog };
}
