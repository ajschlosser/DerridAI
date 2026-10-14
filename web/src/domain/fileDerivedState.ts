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

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Forget everything keyed to a file's records when it is closed or replaced: review selection, row selection, and the
// upsert and store-presence bookkeeping.
export function clearFileDerivedState(state: Loose, fileId: string) {
  state.reviewSelection = new Set(
    [...state.reviewSelection].filter((key: unknown) => !String(key).startsWith(fileId + "::")),
  );
  delete state.selected[fileId];
  for (const bucket of [
    state.upsertState,
    state.upsertIgnored,
    state.storePresence,
    state.storePresenceIds,
    state.storePresenceCheckedAt,
  ]) {
    for (const store of Object.keys(bucket || {})) {
      for (const key of Object.keys(bucket[store] || {}))
        if (key.startsWith(fileId + "::")) delete bucket[store][key];
    }
  }
}
