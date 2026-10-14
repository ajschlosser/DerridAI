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

// Review selection lookups over the loaded workspace files. Both read only the state they are given.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function reviewItemFromKey(state: Any, key: Any) {
  const split = String(key).lastIndexOf("::");
  if (split < 0) return null;
  const fileId = key.slice(0, split),
    index = Number(key.slice(split + 2));
  const file = state.files.find((f: Any) => f.id === fileId);
  if (!file || !Number.isInteger(index) || !file.records[index]) return null;
  return { file, index, record: file.records[index], key };
}

export function selectedReviewItems(state: Any) {
  return [...state.reviewSelection].map((key) => reviewItemFromKey(state, key)).filter(Boolean);
}
